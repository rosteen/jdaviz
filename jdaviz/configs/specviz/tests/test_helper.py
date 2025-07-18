from zipfile import ZipFile

import numpy as np
import pytest
from astropy import units as u
from astropy.io import fits
from astropy.tests.helper import assert_quantity_allclose
from specutils import Spectrum, SpectrumList, SpectrumCollection, SpectralRegion
from astropy.utils.data import download_file

from jdaviz.app import Application
from jdaviz.core.marks import LineUncertainties
from jdaviz import Specviz


class TestSpecvizHelper:
    @pytest.fixture(autouse=True)
    def setup_class(self, specviz_helper, spectrum1d, multi_order_spectrum_list):
        self.spec_app = specviz_helper
        self.spec = spectrum1d
        self.spec_list = SpectrumList([spectrum1d] * 3)
        self.multi_order_spectrum_list = multi_order_spectrum_list

        self.label = "Test 1D Spectrum"
        self.spec_app.load_data(spectrum1d, data_label=self.label)

    def test_load_spectrum1d(self):
        # starts with a single loaded spectrum1d object:
        assert len(self.spec_app.app.data_collection) == 1
        dc_0 = self.spec_app.app.data_collection[0]
        assert dc_0.label == self.label
        assert dc_0.meta['uncertainty_type'] == 'std'

        data = self.spec_app.get_data()

        assert isinstance(data, Spectrum)

    def test_load_hdulist(self):
        # Create a fake fits file with a 1D spectrum for testing.
        primary_header = fits.Header({'TELESCOP': 'Fake Telescope'})
        primary_hdu = fits.PrimaryHDU(header=primary_header)

        # Image extension HDU with a 1D spectrum
        wavelength = np.linspace(5000, 6000, 100)
        flux = np.ones(100)
        spectrum_table = fits.BinTableHDU.from_columns([
            fits.Column(name='WAVELENGTH', array=wavelength, format='E', unit="Angstrom"),
            fits.Column(name='FLUX', array=flux, format='E', unit="Jy")
        ])
        spectrum_table.header['INSTRUME'] = 'Fake Instrument'
        fake_hdulist = fits.HDUList([primary_hdu, spectrum_table])
        self.label = "Test 1D Spectrum"
        self.spec_app.load_data(fake_hdulist)
        data = self.spec_app.get_data(data_label=self.label)
        # HDUList should load as Spectrum
        assert isinstance(data, Spectrum)

    def test_load_spectrum_list_no_labels(self):
        # now load three more spectra from a SpectrumList, without labels
        self.spec_app.load_data(self.spec_list)
        assert len(self.spec_app.app.data_collection) == 4
        for i in (1, 2, 3):
            assert "1D Spectrum" in self.spec_app.app.data_collection[i].label

    def test_load_spectrum_list_with_labels(self):
        # NOTE: will be removed after load_data deprecation is removed
        # now load three more spectra from a SpectrumList, with labels:
        labels = ["List test 1", "List test 2", "List test 3"]
        self.spec_app.load_data(self.spec_list, data_label=labels)
        assert len(self.spec_app.app.data_collection) == 4

    def test_load_multi_order_spectrum_list(self):
        assert len(self.spec_app.app.data_collection) == 1
        # now load ten spectral orders from a SpectrumList:
        self.spec_app.load_data(self.multi_order_spectrum_list)
        assert len(self.spec_app.app.data_collection) == 11

    def test_mismatched_label_length(self):
        # NOTE: will be removed after load_data deprecation is removed
        with pytest.raises(ValueError, match='Length'):
            labels = ["List test 1", "List test 2"]
            self.spec_app.load_data(self.spec_list, data_label=labels)

    def test_load_spectrum_collection(self):
        with pytest.raises(ValueError):
            collection = SpectrumCollection([1]*u.AA)
            self.spec_app.load_data(collection)

    def test_get_spectra(self):
        with pytest.warns(UserWarning, match='Applying the value from the redshift slider'):
            spectra = self.spec_app.get_spectra()

        assert_quantity_allclose(spectra[self.label].flux,
                                 self.spec.flux, atol=1e-5*u.Unit(self.spec.flux.unit))

    def test_get_spectra_no_redshift(self):
        spectra = self.spec_app.get_spectra(apply_slider_redshift=None)

        assert_quantity_allclose(spectra[self.label].flux,
                                 self.spec.flux, atol=1e-5*u.Unit(self.spec.flux.unit))

    def test_get_spectra_no_data_label(self):
        spectra = self.spec_app.get_spectra(data_label=None, apply_slider_redshift=True)

        assert_quantity_allclose(spectra[self.label].flux,
                                 self.spec.flux, atol=1e-5*u.Unit(self.spec.flux.unit))

    def test_get_spectra_label_redshift(self):
        spectra = self.spec_app.get_spectra(data_label=self.label, apply_slider_redshift=True)

        assert_quantity_allclose(spectra.flux,
                                 self.spec.flux, atol=1e-5*u.Unit(self.spec.flux.unit))

    def test_get_spectra_label_redshift_warn(self):
        with pytest.warns(UserWarning, match='Applying the value from the redshift slider'):
            spectra = self.spec_app.get_spectra(data_label=self.label, apply_slider_redshift="Warn")

        assert_quantity_allclose(spectra.flux,
                                 self.spec.flux, atol=1e-5*u.Unit(self.spec.flux.unit))

    def test_get_spectral_regions_none(self):
        plg = self.spec_app.plugins['Subset Tools']
        spec_region = plg.get_regions()

        assert spec_region == {}

    def test_get_spectral_regions_one(self):
        self.spec_app.plugins['Subset Tools'].import_region(
            SpectralRegion(6000*self.spec.spectral_axis.unit, 6500*self.spec.spectral_axis.unit))
        plg = self.spec_app.plugins['Subset Tools']
        spec_region = plg.get_regions()
        assert len(spec_region['Subset 1'].subregions) == 1

    def test_get_spectral_regions_two(self):
        subset = (SpectralRegion(6000*self.spec.spectral_axis.unit,
                                 6500*self.spec.spectral_axis.unit) +
                  SpectralRegion(7300*self.spec.spectral_axis.unit,
                                 7800*self.spec.spectral_axis.unit))
        self.spec_app.plugins['Subset Tools'].import_region(subset, combination_mode='or')

        spec_region = self.spec_app.plugins['Subset Tools'].get_regions()

        assert len(spec_region['Subset 1'].subregions) == 2

    def test_get_spectral_regions_three(self):
        subset = (SpectralRegion(6000*self.spec.spectral_axis.unit,
                                 6400*self.spec.spectral_axis.unit) +
                  SpectralRegion(6600*self.spec.spectral_axis.unit,
                                 7000*self.spec.spectral_axis.unit) +
                  SpectralRegion(7300*self.spec.spectral_axis.unit,
                                 7800*self.spec.spectral_axis.unit))
        self.spec_app.plugins['Subset Tools'].import_region(subset, combination_mode='or')

        spec_region = self.spec_app.plugins['Subset Tools'].get_regions()

        assert len(spec_region['Subset 1'].subregions) == 3
        # Assert correct values for test with 3 subregions
        assert_quantity_allclose(spec_region['Subset 1'].subregions[0][0].value,
                                 6000., atol=1e-5)
        assert_quantity_allclose(spec_region['Subset 1'].subregions[0][1].value,
                                 6400., atol=1e-5)

        assert_quantity_allclose(spec_region['Subset 1'].subregions[1][0].value,
                                 6600., atol=1e-5)
        assert_quantity_allclose(spec_region['Subset 1'].subregions[1][1].value,
                                 7000., atol=1e-5)

        assert_quantity_allclose(spec_region['Subset 1'].subregions[2][0].value,
                                 7300., atol=1e-5)
        assert_quantity_allclose(spec_region['Subset 1'].subregions[2][1].value,
                                 7800., atol=1e-5)

    def test_get_spectral_regions_does_not_raise_value_error(self):
        subset = (SpectralRegion(1*self.spec.spectral_axis.unit,
                                 3*self.spec.spectral_axis.unit) +
                  SpectralRegion(4*self.spec.spectral_axis.unit,
                                 6*self.spec.spectral_axis.unit))
        self.spec_app.plugins['Subset Tools'].import_region(subset, combination_mode='or')

        spec_region = self.spec_app.plugins['Subset Tools'].get_regions()
        assert_quantity_allclose(spec_region['Subset 1'].subregions[0][0].value,
                                 1, atol=1e-5)
        assert_quantity_allclose(spec_region['Subset 1'].subregions[0][1].value,
                                 3, atol=1e-5)

        assert_quantity_allclose(spec_region['Subset 1'].subregions[1][0].value,
                                 4, atol=1e-5)
        assert_quantity_allclose(spec_region['Subset 1'].subregions[1][1].value,
                                 6, atol=1e-5)

    def test_get_spectral_regions_composite_region(self):
        subset = (SpectralRegion(6000*self.spec.spectral_axis.unit,
                                 7400*self.spec.spectral_axis.unit) +
                  SpectralRegion(6600*self.spec.spectral_axis.unit,
                                 7000*self.spec.spectral_axis.unit) +
                  SpectralRegion(7300*self.spec.spectral_axis.unit,
                                 7800*self.spec.spectral_axis.unit))
        self.spec_app.plugins['Subset Tools'].import_region(
            subset, combination_mode=['new', 'andnot', 'and'])

        spec_region = self.spec_app.plugins['Subset Tools'].get_regions()

        assert len(spec_region['Subset 1'].subregions) == 1
        # Assert correct values for test with 3 subregions
        assert_quantity_allclose(spec_region['Subset 1'].subregions[0][0].value,
                                 7300., atol=1e-5)
        assert_quantity_allclose(spec_region['Subset 1'].subregions[0][1].value,
                                 7400., atol=1e-5)

    def test_get_spectral_regions_composite_region_multiple_and_nots(self):
        subset = (SpectralRegion(6000*self.spec.spectral_axis.unit,
                                 7800*self.spec.spectral_axis.unit) +
                  SpectralRegion(6200*self.spec.spectral_axis.unit,
                                 6600*self.spec.spectral_axis.unit) +
                  SpectralRegion(7300*self.spec.spectral_axis.unit,
                                 7700*self.spec.spectral_axis.unit))
        self.spec_app.plugins['Subset Tools'].import_region(
            subset, combination_mode=['new', 'andnot', 'andnot'])

        spec_region = self.spec_app.plugins['Subset Tools'].get_regions()

        assert len(spec_region['Subset 1'].subregions) == 3
        # Assert correct values for test with 3 subregions
        assert_quantity_allclose(spec_region['Subset 1'].subregions[0][0].value,
                                 6000., atol=1e-5)
        assert_quantity_allclose(spec_region['Subset 1'].subregions[0][1].value,
                                 6200., atol=1e-5)

        assert_quantity_allclose(spec_region['Subset 1'].subregions[1][0].value,
                                 6600., atol=1e-5)
        assert_quantity_allclose(spec_region['Subset 1'].subregions[1][1].value,
                                 7300., atol=1e-5)
        assert_quantity_allclose(spec_region['Subset 1'].subregions[2][0].value,
                                 7700., atol=1e-5)
        assert_quantity_allclose(spec_region['Subset 1'].subregions[2][1].value,
                                 7800., atol=1e-5)


def test_get_spectra_no_spectra(specviz_helper, spectrum1d):
    with pytest.warns(UserWarning, match='Applying the value from the redshift slider'):
        spectra = specviz_helper.get_spectra()

    assert spectra == {}


def test_get_spectra_no_spectra_redshift_error(specviz_helper, spectrum1d):
    spectra = specviz_helper.get_spectra(apply_slider_redshift=True)

    assert spectra == {}


def test_get_spectra_no_spectra_label(specviz_helper, spectrum1d):
    label = "label"
    with pytest.raises(ValueError):
        specviz_helper.get_spectra(data_label=label)


def test_get_spectra_no_spectra_label_redshift_error(specviz_helper, spectrum1d):
    label = "label"
    with pytest.raises(ValueError):
        specviz_helper.get_spectra(data_label=label, apply_slider_redshift=True)


def test_add_spectrum_after_subset(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d, data_label="test")
    subset = SpectralRegion(6200 * spectrum1d.spectral_axis.unit,
                            7000 * spectrum1d.spectral_axis.unit)
    specviz_helper.plugins['Subset Tools'].import_region(subset)

    new_spec = specviz_helper.get_spectra(apply_slider_redshift=True)["test"]*0.9
    specviz_helper.load_data(new_spec, data_label="test2")


def test_get_spectral_regions_unit(specviz_helper, spectrum1d):
    # Ensure units we put in are the same as the units we get out
    specviz_helper.load_data(spectrum1d)
    subset = SpectralRegion(6200 * spectrum1d.spectral_axis.unit,
                            7000 * spectrum1d.spectral_axis.unit)
    specviz_helper.plugins['Subset Tools'].import_region(subset)

    subsets = specviz_helper.plugins['Subset Tools'].get_regions()
    reg = subsets.get('Subset 1')

    assert spectrum1d.spectral_axis.unit == reg.lower.unit
    assert spectrum1d.spectral_axis.unit == reg.upper.unit


def test_get_spectral_regions_unit_conversion(specviz_helper, spectrum1d):
    spec_viewer = specviz_helper.app.get_viewer('spectrum-viewer')

    # Mouseover without data should not crash.
    label_mouseover = specviz_helper._coords_info
    label_mouseover._viewer_mouse_event(spec_viewer,
                                        {'event': 'mousemove', 'domain': {'x': 6100, 'y': 12.5}})
    assert label_mouseover.as_text() == ('', '', '')
    assert label_mouseover.icon == ''

    # If the reference (visible) data changes via unit conversion,
    # check that the region's units convert too
    specviz_helper.load_data(spectrum1d)  # Originally Angstrom

    # Also check coordinates info panel.
    # x=0 -> 6000 A, x=1 -> 6222.222 A
    label_mouseover._viewer_mouse_event(spec_viewer,
                                        {'event': 'mousemove', 'domain': {'x': 6100, 'y': 12.5}})
    assert label_mouseover.as_text() == ('Cursor 6.10000e+03, 1.25000e+01',
                                         'Wave 6.00000e+03 Angstrom (0 pix)',  # actual 0.4
                                         'Flux 1.24967e+01 Jy')
    assert label_mouseover.icon == 'a'

    label_mouseover._viewer_mouse_event(spec_viewer,
                                        {'event': 'mousemove', 'domain': {'x': None, 'y': 12.5}})
    assert label_mouseover.as_text() == ('', '', '')
    assert label_mouseover.icon == ''

    # Convert the wavelength axis to micron
    new_spectral_axis = "um"
    specviz_helper.plugins['Unit Conversion'].spectral_unit = new_spectral_axis
    spectral_axis_unit = u.Unit(specviz_helper.plugins['Unit Conversion'].spectral_unit.selected)
    subset = SpectralRegion(0.6 * spectral_axis_unit, 0.7 * spectral_axis_unit)
    specviz_helper.plugins['Subset Tools'].import_region(subset)

    # Retrieve the Subset
    ss = specviz_helper.plugins['Subset Tools'].get_regions(use_display_units=False)
    reg = ss.get('Subset 1')
    assert reg.lower.unit == u.Angstrom
    assert reg.upper.unit == u.Angstrom

    ss = specviz_helper.plugins['Subset Tools'].get_regions(use_display_units=True)
    reg = ss.get('Subset 1')
    assert reg.lower.unit == u.um
    assert reg.upper.unit == u.um

    # Coordinates info panel should show new unit
    label_mouseover._viewer_mouse_event(spec_viewer,
                                        {'event': 'mousemove', 'domain': {'x': 0.61, 'y': 12.5}})
    label_mouseover.as_text() == ('Cursor 6.10000e-01, 1.25000e+01',
                                  'Wave 6.00000e-01 micron (0 pix)',
                                  'Flux 1.24967e+01 Jy')
    assert label_mouseover.icon == 'a'

    label_mouseover._viewer_mouse_event(spec_viewer, {'event': 'mouseleave'})
    assert label_mouseover.as_text() == ('', '', '')
    assert label_mouseover.icon == ''


def test_subset_default_thickness(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d)

    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    sv.toolbar.active_tool = sv.toolbar.tools['bqplot:xrange']

    spectral_axis_unit = u.Unit(specviz_helper.plugins['Unit Conversion'].spectral_unit.selected)
    subset = SpectralRegion(2.5 * spectral_axis_unit,
                            3.5 * spectral_axis_unit)
    specviz_helper.plugins['Subset Tools'].import_region(subset)
    # _on_layers_update is not triggered within CI
    sv._on_layers_update()
    assert sv.state.layers[-1].linewidth == 3


def test_app_links(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d)
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    assert isinstance(sv.jdaviz_app, Application)
    assert isinstance(sv.jdaviz_helper, Specviz)


@pytest.mark.remote_data
@pytest.mark.xfail(reason='Multiple file support not yet implemented in loaders')
def test_load_spectrum_list_directory(tmpdir, specviz_helper):
    # niriss_parser_test_data.zip
    test_data = 'https://stsci.box.com/shared/static/7ndets0vjjsa97la2hvjvm6xvnu5b594.zip'
    fn = download_file(test_data, cache=True, timeout=30)
    with ZipFile(fn, 'r') as sample_data_zip:
        sample_data_zip.extractall(tmpdir.strpath)
    data_path = str(tmpdir.join('NIRISS_for_parser_p0171'))

    # Load two NIRISS x1d files from FITS. They have 19 and 20 EXTRACT1D
    # extensions per file, for a total of 39 spectra to load:
    with pytest.warns(UserWarning, match='SRCTYPE is missing or UNKNOWN in JWST x1d loader'):
        specviz_helper.load_data(data_path)

    # NOTE: the length was 3 before specutils 1.9 (https://github.com/astropy/specutils/pull/982)
    expected_len = 39
    assert len(specviz_helper.app.data_collection) == expected_len

    for data in specviz_helper.app.data_collection:
        assert data.main_components[:2] == ['flux', 'uncertainty']

    dc_0 = specviz_helper.app.data_collection[0]
    assert 'header' not in dc_0.meta
    assert dc_0.meta['SPORDER'] == 1


@pytest.mark.remote_data
@pytest.mark.xfail(reason='Multiple file support not yet implemented in loaders')
def test_load_spectrum_list_directory_concat(tmpdir, specviz_helper):
    # niriss_parser_test_data.zip
    test_data = 'https://stsci.box.com/shared/static/7ndets0vjjsa97la2hvjvm6xvnu5b594.zip'
    fn = download_file(test_data, cache=True, timeout=30)
    with ZipFile(fn, 'r') as sample_data_zip:
        sample_data_zip.extractall(tmpdir.strpath)
    data_path = str(tmpdir.join('NIRISS_for_parser_p0171'))

    # Load two x1d files from FITS. They have 19 and 20 EXTRACT1D
    # extensions per file, for a total of 39 spectra to load. Also concatenate
    # spectra common to each file into one "Combined" spectrum to load per file.
    # Now the total is (19 EXTRACT 1D + 1 Combined) + (20 EXTRACT 1D + 1 Combined) = 41.
    with pytest.warns(UserWarning, match='SRCTYPE is missing or UNKNOWN in JWST x1d loader'):
        specviz_helper.load_data(data_path, concat_by_file=True)
    assert len(specviz_helper.app.data_collection) == 41


def test_load_2d_flux(specviz_helper):
    # Test loading a spectrum with a 2D flux, which should be split into separate
    # 1D Spectrum objects to load in Specviz.
    spec = Spectrum(spectral_axis=np.linspace(4000, 6000, 10)*u.Angstrom,
                    flux=np.ones((4, 10))*u.Unit("1e-17 erg / (Angstrom cm2 s)"))
    specviz_helper.load_data(spec, data_label="test")

    assert len(specviz_helper.app.data_collection) == 4
    assert specviz_helper.app.data_collection[0].label == "test_0"

    spec2 = Spectrum(spectral_axis=np.linspace(4000, 6000, 10)*u.Angstrom,
                     flux=np.ones((2, 10))*u.Unit("1e-17 erg / (Angstrom cm2 s)"))

    # Make sure 2D spectra in a SpectrumList also get split properly.
    spec_list = SpectrumList([spec, spec2])
    specviz_helper.load_data(spec_list, data_label="second test")

    assert len(specviz_helper.app.data_collection) == 10
    assert specviz_helper.app.data_collection[-1].label == "second test_5"


def test_plot_uncertainties(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d)

    specviz_viewer = specviz_helper.app.get_viewer('spectrum-viewer')

    assert len([m for m in specviz_viewer.figure.marks if isinstance(m, LineUncertainties)]) == 0

    specviz_viewer.state.show_uncertainty = True
    uncert_marks = [m for m in specviz_viewer.figure.marks if isinstance(m, LineUncertainties)]
    assert len(uncert_marks) == 1
    # mark has a lower and upper boundary, but each should have the same length as the spectrum
    assert len(uncert_marks[0].x[0]) == len(spectrum1d.flux)

    # enable as-steps and make sure doesn't crash (won't change the number of marks)
    specviz_viewer.state.layers[0].as_steps = True
    specviz_viewer._plot_uncertainties()
    uncert_marks = [m for m in specviz_viewer.figure.marks if isinstance(m, LineUncertainties)]
    assert len(uncert_marks) == 1
    # now the mark should have double the length as its drawn on the bin edges
    assert len(uncert_marks[0].x[0]) == len(spectrum1d.flux) * 2

    specviz_viewer.state.show_uncertainty = False

    assert len([m for m in specviz_viewer.figure.marks if isinstance(m, LineUncertainties)]) == 0


# Some API might be going through deprecation, so ignore the warning.
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_plugin_user_apis(specviz_helper):
    for plugin_name, plugin_api in specviz_helper.plugins.items():
        plugin = plugin_api._obj
        for attr in plugin_api._expose:
            assert hasattr(plugin, attr)


def test_data_label_as_posarg(specviz_helper, spectrum1d):
    # Passing in data_label keyword as posarg.
    specviz_helper.load_data(spectrum1d, 'my_spec')
    assert specviz_helper.app.data_collection[0].label == 'my_spec'


def test_spectra_partial_overlap(specviz_helper):
    spec_viewer = specviz_helper.app.get_viewer('spectrum-viewer')

    wave_1 = np.linspace(6000, 7000, 10) * u.AA
    flux_1 = ([1200] * wave_1.size) * u.nJy
    sp_1 = Spectrum(flux=flux_1, spectral_axis=wave_1)

    wave_2 = wave_1 + (800 * u.AA)
    flux_2 = ([60] * wave_2.size) * u.nJy
    sp_2 = Spectrum(flux=flux_2, spectral_axis=wave_2)

    specviz_helper.load_data(sp_1, data_label='left')
    specviz_helper.load_data(sp_2, data_label='right')

    # Test mouseover outside of left but in range for right.
    # Should show right spectrum even when mouse is near left flux.
    label_mouseover = specviz_helper._coords_info
    label_mouseover._viewer_mouse_event(spec_viewer,
                                        {'event': 'mousemove', 'domain': {'x': 7022, 'y': 1000}})
    assert label_mouseover.as_text() == ('Cursor 7.02200e+03, 1.00000e+03',
                                         'Wave 7.02222e+03 Angstrom (2 pix)',
                                         'Flux 6.00000e+01 nJy')
    assert label_mouseover.icon == 'b'


def test_spectra_incompatible_flux(specviz_helper):
    """https://github.com/spacetelescope/jdaviz/issues/2459"""
    wav = [1.1, 1.2, 1.3] * u.um
    sp1 = Spectrum(flux=[1, 1.1, 1] * (u.MJy / u.sr), spectral_axis=wav)
    sp2 = Spectrum(flux=[1, 1, 1.1] * (u.MJy), spectral_axis=wav)
    flux3 = ([1, 1.1, 1] * u.MJy).to(u.erg / u.s / u.cm / u.cm / u.AA, u.spectral_density(wav))
    sp3 = Spectrum(flux=flux3, spectral_axis=wav)

    specviz_helper.load_data(sp2, data_label="2")  # OK
    specviz_helper.load_data(sp1, data_label="1")  # Not OK
    specviz_helper.load_data(sp3, data_label="3")  # OK

    # all 3 load into data-collection, but only two in the viewer (with snackbar error)
    assert len(specviz_helper.app.data_collection.labels) == 3
    assert len(specviz_helper.viewers['spectrum-viewer']._obj.layers) == 2


def test_delete_data_with_subsets(specviz_helper, spectrum1d, spectrum1d_nm):
    specviz_helper.load_data(spectrum1d, 'my_spec_AA')
    specviz_helper.load_data(spectrum1d_nm, 'my_spec_nm')

    spectral_axis_unit = u.Unit(specviz_helper.plugins['Unit Conversion'].spectral_unit.selected)

    subset = SpectralRegion(6200 * spectral_axis_unit,
                            7000 * spectral_axis_unit)
    specviz_helper.plugins['Subset Tools'].import_region(subset)

    assert len(specviz_helper.app.data_collection.subset_groups) == 1
    subset1 = specviz_helper.app.data_collection.subset_groups[0]
    assert subset1.subset_state.att.parent.label == "my_spec_AA"
    np.testing.assert_allclose((subset1.subset_state.lo, subset1.subset_state.hi), (6200, 7000))

    specviz_helper.app.remove_data_from_viewer('spectrum-viewer', "my_spec_AA")
    specviz_helper.app.data_item_remove("my_spec_AA")

    # Check that the reparenting and coordinate recalculations happened
    assert subset1.subset_state.att.parent.label == "my_spec_nm"
    np.testing.assert_allclose((subset1.subset_state.lo, subset1.subset_state.hi), (620, 700))
