"""
Tests the features of the Model Fitting Plugin (Selecting model parameters, adding models, etc.)
This does NOT test the actual fitting self (see test_fitting.py for that)
"""
import warnings
import pytest
from contextlib import nullcontext

import numpy as np
from numpy.testing import assert_allclose

from astropy.nddata import StdDevUncertainty
from astropy.utils.exceptions import AstropyUserWarning
from astropy.utils.introspection import minversion
import astropy.units as u

from glue.core.roi import CircularROI
from specutils import Spectrum, SpectralRegion

from jdaviz.configs.default.plugins.model_fitting.initializers import MODELS

PYTEST_LT_8_0 = not minversion(pytest, "8.0.dev")


def test_default_model_labels(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d)
    modelfit_plugin = specviz_helper.plugins['Model Fitting']
    # By default, the spectral region should be the entire spectrum
    assert modelfit_plugin._obj.spectral_subset_selected == "Entire Spectrum"

    for model in MODELS:
        # Check that the auto label is set correctly (or at least the first character matches)
        # BlackBody and Polynomial labels behave differently, so check only the first character
        modelfit_plugin._obj.model_comp_selected = model
        assert modelfit_plugin._obj.comp_label[0] == model[0]

        # Test component label increments by default
        previous_label = modelfit_plugin._obj.comp_label
        modelfit_plugin._obj.vue_add_model({})
        assert modelfit_plugin._obj.comp_label == previous_label + "_1"

    assert len(modelfit_plugin._obj.component_models) == len(MODELS)

    # Test that default equation adds all components together
    assert (
        modelfit_plugin._obj.model_equation
        == "+".join(param["id"] for param in modelfit_plugin._obj.component_models)
    )


def test_custom_model_labels(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d)
    modelfit_plugin = specviz_helper.plugins['Model Fitting']

    for i, model in enumerate(MODELS):
        # Add one of each model with a unique name
        modelfit_plugin._obj.model_comp_selected = model
        modelfit_plugin._obj.comp_label = f"test_model_{i}"
        modelfit_plugin._obj.vue_add_model({})

    assert len(modelfit_plugin._obj.component_models) == len(MODELS)

    # Test that default equation adds all components together
    assert (
        modelfit_plugin._obj.model_equation
        == "+".join(param["id"] for param in modelfit_plugin._obj.component_models)
    )


def test_register_model_with_uncertainty_weighting(specviz_helper, spectrum1d):
    spectrum1d.uncertainty = StdDevUncertainty(spectrum1d.flux * 0.1)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        specviz_helper.load_data(spectrum1d)
    modelfit_plugin = specviz_helper.plugins['Model Fitting']

    # Test registering a simple linear fit
    modelfit_plugin._obj.model_comp_selected = 'Linear1D'
    modelfit_plugin._obj.vue_add_model({})
    with pytest.warns(AstropyUserWarning, match='Model is linear in parameters'):
        modelfit_plugin.calculate_fit()
    assert len(specviz_helper.app.data_collection) == 2

    # Test fitting again overwrites original fit
    with pytest.warns(AstropyUserWarning, match='Model is linear in parameters'):
        modelfit_plugin.calculate_fit()
    assert len(specviz_helper.app.data_collection) == 2

    # Test custom model label
    test_label = 'my_Linear1D'
    modelfit_plugin._obj.results_label = test_label
    with pytest.warns(AstropyUserWarning, match='Model is linear in parameters'):
        modelfit_plugin.calculate_fit()
    assert test_label in specviz_helper.app.data_collection

    # Test that the parameter uncertainties were updated
    expected_uncertainties = {'slope': 0.0007063584243707317, 'intercept': 4.885421320000062}
    result_model = modelfit_plugin._obj.component_models[0]
    for param in result_model["parameters"]:
        assert np.allclose(param["std"], expected_uncertainties[param["name"]], rtol=0.01)


def test_register_model_uncertainty_is_none(specviz_helper, spectrum1d):
    # Set uncertainty to None
    spectrum1d.uncertainty = None
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        specviz_helper.load_data(spectrum1d)
    modelfit_plugin = specviz_helper.plugins['Model Fitting']

    # Test registering a simple linear fit
    modelfit_plugin._obj.model_comp_selected = 'Linear1D'
    modelfit_plugin._obj.vue_add_model({})
    with pytest.warns(AstropyUserWarning, match='Model is linear in parameters'):
        modelfit_plugin.calculate_fit()
    assert len(specviz_helper.app.data_collection) == 2

    # Test fitting again overwrites original fit
    with pytest.warns(AstropyUserWarning, match='Model is linear in parameters'):
        modelfit_plugin.calculate_fit()
    assert len(specviz_helper.app.data_collection) == 2

    # Test custom model label
    test_label = 'my_Linear1D'
    modelfit_plugin._obj.results_label = test_label
    with pytest.warns(AstropyUserWarning, match='Model is linear in parameters'):
        modelfit_plugin.calculate_fit()
    assert test_label in specviz_helper.app.data_collection

    # Test that the parameter uncertainties were updated
    expected_uncertainties = {'slope': 0.00038, 'intercept': 2.67}
    result_model = modelfit_plugin._obj.component_models[0]
    for param in result_model["parameters"]:
        assert np.allclose(param["std"], expected_uncertainties[param["name"]], rtol=0.01)


def test_register_cube_model(cubeviz_helper, spectrum1d_cube):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        cubeviz_helper.load_data(spectrum1d_cube)
    modelfit_plugin = cubeviz_helper.plugins['Model Fitting']

    # Test custom model label
    modelfit_plugin.create_model_component('Linear1D', 'L')
    test_label = 'my_Linear1D'
    modelfit_plugin._obj.results_label = test_label
    # changing the lable should set auto to False, but the event may not have triggered yet
    modelfit_plugin._obj.results_label_auto = False
    modelfit_plugin.cube_fit = True
    modelfit_plugin.reestimate_model_parameters()
    assert modelfit_plugin._obj.results_label_default == 'model'
    assert modelfit_plugin._obj.results_label == test_label

    modelfit_plugin._obj.parallel_n_cpu = 1
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', message='.*Model is linear in parameters.*')
        modelfit_plugin.calculate_fit()
    assert test_label in cubeviz_helper.app.data_collection


def test_initialize_gaussian_with_cube(cubeviz_helper, spectrum1d_cube_larger):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        cubeviz_helper.load_data(spectrum1d_cube_larger)
    modelfit_plugin = cubeviz_helper.plugins['Model Fitting']

    modelfit_plugin.cube_fit = True
    # Check that we can initialize a Gaussian1D with cube fit toggled on
    modelfit_plugin.create_model_component('Gaussian1D', 'G')


def test_fit_cube_no_wcs(cubeviz_helper):
    # This is like when user do something to a cube outside of Jdaviz
    # and then load it back into a new instance of Cubeviz for further analysis.
    sp = Spectrum(flux=np.ones((7, 8, 9)) * u.nJy, spectral_axis_index=2)  # ny, nx, nz
    cubeviz_helper.load_data(sp, data_label="test_cube")
    mf = cubeviz_helper.plugins['Model Fitting']
    mf.create_model_component('Linear1D')
    mf.cube_fit = True
    # Need to manually reestimate the parameters to update the units
    mf.reestimate_model_parameters()

    mf._obj.parallel_n_cpu = 1
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Model is linear in parameters.*")
        fitted_model, output_cube = mf.calculate_fit(add_data=True)
    assert len(fitted_model) == 56  # ny * nx
    # Make sure shapes are all self-consistent within Cubeviz instance.
    fitted_data = cubeviz_helper.app.data_collection["model"]
    assert fitted_data.shape == (7, 8, 9)  # nx, ny, nz
    assert fitted_data.shape == cubeviz_helper.app.data_collection[0].shape
    assert fitted_data.shape == output_cube.shape


def test_toggle_cube_fit_subset(cubeviz_helper):
    sp = Spectrum(flux=np.ones((7, 8, 9)) * u.nJy, spectral_axis_index=2)  # ny, nx, nz
    cubeviz_helper.load_data(sp, data_label="test_cube")
    mf = cubeviz_helper.plugins['Model Fitting']

    unit = u.Unit(cubeviz_helper.plugins['Unit Conversion'].spectral_unit.selected)
    cubeviz_helper.plugins['Subset Tools'].import_region(SpectralRegion(7.5 * unit,
                                                                        8 * unit))

    mf.spectral_subset = 'Subset 1'
    mf.cube_fit = True


def test_refit_plot_options(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d)
    modelfit_plugin = specviz_helper.plugins['Model Fitting']

    modelfit_plugin._obj.model_comp_selected = 'Const1D'
    modelfit_plugin._obj.comp_label = "C"
    modelfit_plugin._obj.vue_add_model({})

    with pytest.warns(AstropyUserWarning):
        modelfit_plugin.calculate_fit(add_data=True)

    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    atts = {"color": "red", "linewidth": 2, "alpha": 0.8}
    layer_state = [layer.state for layer in sv.layers if layer.layer.label == "model"][0]
    for att in atts:
        setattr(layer_state, att, atts[att])

    # Refit using the same name, which will replace the data by default.
    modelfit_plugin.create_model_component('Linear1D', 'L')

    with pytest.warns(AstropyUserWarning):
        modelfit_plugin.calculate_fit(add_data=True)

    layer_state = [layer.state for layer in sv.layers if layer.layer.label == "model"][0]

    for att in atts:
        assert atts[att] == getattr(layer_state, att)


def test_user_api(specviz_helper, spectrum1d):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        specviz_helper.load_data(spectrum1d)
    p = specviz_helper.plugins['Model Fitting']

    with pytest.raises(ValueError, match="blah is not a valid attribute and cannot be set"):
        p.blah = 5

    # even though the default label is set to C, adding Linear1D should default to its automatic
    # default label of 'L'
    assert p.model_component == 'Const1D'  # tests SelectPluginComponent's __eq__
    assert p.model_component_label.value == 'C'
    assert p.model_component_label == 'C'  # tests AutoTextField's __eq__
    p.create_model_component('Linear1D')
    assert p.model_components == ['L']

    with pytest.raises(ValueError, match='poly_order should only be passed if model_component is Polynomial1D'):  # noqa
        p.create_model_component('Linear1D', poly_order=2)

    with pytest.raises(ValueError, match="model component label 'L' already in use"):
        p.create_model_component('Linear1D', 'L')

    with pytest.raises(ValueError, match="model component with label 'dne' does not exist"):
        p.remove_model_component('dne')

    p.remove_model_component('L')
    assert len(p.model_components) == 0

    p.create_model_component('Polynomial1D', poly_order=2)
    assert p.model_components == ['P2']

    with pytest.raises(ValueError, match="'dne' is not a label of an existing model component"):
        p.get_model_component('dne')

    p.get_model_component('P2')
    p.set_model_component('P2', 'c0', value=0.2, fixed=True)
    assert p.get_model_component('P2', 'c0')['value'] == 0.2
    assert p.get_model_component('P2', 'c0')['fixed'] is True


def test_fit_gaussian_with_fixed_mean(specviz_helper, spectrum1d):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        specviz_helper.load_data(spectrum1d)
    modelfit_plugin = specviz_helper.plugins['Model Fitting']

    modelfit_plugin.create_model_component('Gaussian1D', 'G')
    params = modelfit_plugin._obj.component_models[0]['parameters']
    params[1]['fixed'] = True  # Fix mean

    old_amp = params[0]['value']
    old_mean = params[1]['value']
    old_std = params[2]['value']

    modelfit_plugin.residuals_calculate = True
    result, spectrum, resids = modelfit_plugin.calculate_fit()

    # Make sure mean is really fixed.
    assert_allclose(result.mean.value, old_mean)
    assert not np.allclose((result.amplitude.value, result.stddev.value), (old_amp, old_std))


def test_reestimate_parameters(specviz_helper, spectrum1d):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        specviz_helper.load_data(spectrum1d)
    mf = specviz_helper.plugins['Model Fitting']

    mf.create_model_component('Gaussian1D', 'G')
    mf.set_model_component('G', 'stddev', value=1, fixed=True)
    mc = mf.get_model_component('G')

    assert_allclose(mc['parameters']['mean']['value'], 7055.519926198364)
    assert mc['parameters']['stddev']['value'] == 1
    assert mc['parameters']['stddev']['fixed'] is True

    unit = u.Unit(specviz_helper.plugins['Unit Conversion'].spectral_unit.selected)
    specviz_helper.plugins['Subset Tools'].import_region(SpectralRegion(7500 * unit,
                                                                        8000 * unit))

    mf.spectral_subset = 'Subset 1'

    mf.reestimate_model_parameters()
    mc = mf.get_model_component('G')

    # mean should change, stddev should not
    assert_allclose(mc['parameters']['mean']['value'], 7780.8838070125375)
    assert mc['parameters']['stddev']['value'] == 1
    assert mc['parameters']['stddev']['fixed'] is True


def test_subset_masks(cubeviz_helper, spectrum1d_cube_larger):
    cubeviz_helper.load_data(spectrum1d_cube_larger)
    assert spectrum1d_cube_larger.mask is None

    # create a "Subset 1" entry in spatial dimension, selected "interactively"
    cubeviz_helper.plugins['Subset Tools'].import_region(CircularROI(0.5, 0.5, 1))

    # check that when no subset is selected, the spectral cube has no mask:
    p = cubeviz_helper.app.get_tray_item_from_name('g-model-fitting')

    sv = cubeviz_helper.app.get_viewer('spectrum-viewer')
    # create a "Subset 2" entry in spectral dimension, selected "interactively"
    min_wavelength = 4625 * u.AA
    max_wavelength = spectrum1d_cube_larger.wavelength.max()

    # This toolbar selection allows the XRangeROI call below to create a
    # new subset, rather than replacing the previous subset:
    sv.toolbar_active_subset.selected = []

    # Now create the new spectral subset:
    cubeviz_helper.plugins['Subset Tools'].import_region(
        SpectralRegion(min_wavelength.to(u.m), max_wavelength.to(u.m)))
    assert "Subset 2" in p.spectral_subset.choices

    # Select the spectral subset
    p.spectral_subset_selected = "Subset 2"

    # Get the data object again (ensures mask == None)
    data = cubeviz_helper.app.data_collection[-1].get_object()
    subset = cubeviz_helper.app.data_collection[-1].get_subset_object(
        p.spectral_subset_selected, cls=Spectrum, statistic=None
    )
    masked_data = p._apply_subset_masks(data, p.spectral_subset)

    expected_spectral_mask = np.ones(data.flux.shape).astype(bool)
    expected_spectral_mask[3:] = False

    assert np.all(masked_data.mask == expected_spectral_mask)
    assert np.all(subset.mask == expected_spectral_mask)


def test_invalid_subset(specviz_helper, spectrum1d):
    # 6000-8000
    specviz_helper.load_data(spectrum1d, data_label="right_spectrum")

    # 5000-7000
    sp2 = Spectrum(spectral_axis=spectrum1d.spectral_axis - 1000*spectrum1d.spectral_axis.unit,
                   flux=spectrum1d.flux * 1.25)
    specviz_helper.load_data(sp2, data_label="left_spectrum")

    # apply subset that overlaps on left_spectrum, but not right_spectrum
    # NOTE: using a subset that overlaps the right_spectrum (reference) results in errors when
    # retrieving the subset (https://github.com/spacetelescope/jdaviz/issues/1868)
    unit = u.Unit(specviz_helper.plugins['Unit Conversion'].spectral_unit.selected)
    specviz_helper.plugins['Subset Tools'].import_region(SpectralRegion(5000 * unit,
                                                                        6000 * unit))

    plugin = specviz_helper.plugins['Model Fitting']
    plugin.create_model_component('Linear1D')

    plugin.dataset = 'right_spectrum'
    assert plugin.dataset == 'right_spectrum'
    assert plugin.spectral_subset == 'Entire Spectrum'
    assert plugin._obj.spectral_subset_valid

    plugin.spectral_subset = 'Subset 1'
    assert not plugin._obj.spectral_subset_valid

    with pytest.raises(ValueError, match=r"spectral subset 'Subset 1' \(5000.0, 6000.0\) is outside data range of 'right_spectrum' \(6000.0, 8000.0\)"):  # noqa
        plugin.calculate_fit()

    plugin.dataset = 'left_spectrum'
    assert plugin._obj.spectral_subset_valid


def test_all_nan_uncert(specviz_helper):

    # test that if you have a fully finite data array, and a fully nan/inf
    # uncert array, that it is set to None and the fit proceeds (rather than
    # being filtered in the fitter, as would normally happen with nans)

    uncertainty = StdDevUncertainty([np.nan, np.nan, np.nan, np.nan, np.nan, np.nan] * u.Jy)
    spec = Spectrum(flux=[1, 2, 3, 4, 5, 6]*u.Jy, uncertainty=uncertainty)
    specviz_helper.load_data(spec)

    plugin = specviz_helper.plugins['Model Fitting']
    plugin.create_model_component('Linear1D')

    with pytest.warns(AstropyUserWarning, match='Model is linear in parameters'):
        plugin.calculate_fit()

    # check that slope and intercept are fit correctly
    plugin._obj.component_models[0]['parameters'][0]['value'] == 1.0
    plugin._obj.component_models[0]['parameters'][1]['value'] == 1.0

    # and that this value is correctly set to false, even though there IS
    # a mismatch, since its the entire array it will be reset
    assert plugin._obj.non_finite_uncertainty_mismatch is False


def test_all_nan_uncert_subset(specviz_helper):

    # test that nans in uncertainty array are filtered from fit (contrary to
    # what is tested in test_all_nan_uncert, when its not the entire array they
    # SHOULD be filtered even when corresponding data values are finite), and that
    # the `non_finite_uncertainty_mismatch` traitlet is True to trigger a warning
    # message

    uncertainty = StdDevUncertainty([1, 1, np.nan, np.nan, np.nan, np.nan] * u.Jy)
    spec = Spectrum(flux=[2, 4, 3, 4, 5, 6]*u.Jy, uncertainty=uncertainty)
    specviz_helper.load_data(spec)

    plugin = specviz_helper.plugins['Model Fitting']
    plugin.create_model_component('Linear1D')

    if PYTEST_LT_8_0:
        ctx = nullcontext()
    else:
        ctx = pytest.warns(
            AstropyUserWarning, match="Non-Finite input data has been removed by the fitter")

    with pytest.warns(AstropyUserWarning, match='Model is linear in parameters'), ctx:
        plugin.calculate_fit()

    # check that slope and intercept are fit correctly to just the first 2
    # data points
    plugin._obj.component_models[0]['parameters'][0]['value'] == 2.0
    plugin._obj.component_models[0]['parameters'][1]['value'] == 2.0

    # # and that this value is correctly set to false, even though there IS
    # # a mismatch, since its the entire array it will be reset
    assert plugin._obj.non_finite_uncertainty_mismatch is True
