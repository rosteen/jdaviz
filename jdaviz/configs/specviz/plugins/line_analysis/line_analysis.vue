<template>
  <j-tray-plugin
    :config="config"
    plugin_key="Line Analysis"
    :api_hints_enabled.sync="api_hints_enabled"
    :description="docs_description"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#line-analysis'"
    :uses_active_status="uses_active_status"
    @plugin-ping="plugin_ping($event)"
    :keep_active.sync="keep_active"
    :disabled_msg="disabled_msg"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to">

    <j-plugin-section-header>Line</j-plugin-section-header>
    <v-row>
      <j-docs-link>Choose a region that defines the spectral line.</j-docs-link>
    </v-row>

    <!-- for mosviz, the entries change on row change, so we want to always show the dropdown
         to make sure that is clear -->
    <plugin-dataset-select
      :items="dataset_items"
      :selected.sync="dataset_selected"
      :show_if_single_entry="config=='mosviz'"
      label="Data"
      api_hint="plg.dataset ="
      :api_hints_enabled="api_hints_enabled"
      hint="Select the data set to be analysed."
    />

    <plugin-subset-select
      :items="spectral_subset_items"
      :selected.sync="spectral_subset_selected"
      :show_if_single_entry="true"
      label="Spectral region"
      api_hint="plg.spectral_subset ="
      :api_hints_enabled="api_hints_enabled"
      hint="Select spectral region that defines the line."
    />

    <v-row v-if="!spectral_subset_valid">
      <span class="v-messages v-messages__message text--secondary" style="color: red !important">
          Selected dataset and spectral subset do not overlap
      </span>
    </v-row>

    <j-plugin-section-header>Continuum</j-plugin-section-header>
    <v-row>
      <j-docs-link>
        {{continuum_subset_selected=='Surrounding' && spectral_subset_selected=='Entire Spectrum' ? "Since using the entire spectrum, the end points will be used to fit a linear continuum." : "Choose a region to fit a linear line as the underlying continuum."}}
        {{continuum_subset_selected=='Surrounding' && spectral_subset_selected!='Entire Spectrum' ? "Choose a width in number of data points to consider on each side of the line region defined above." : null}}
        When this plugin is opened, a visual indicator will show on the spectrum plot showing the continuum fitted as a thick line, and interpolated into the line region as a thin line.
      </j-docs-link>
    </v-row>

    <plugin-subset-select
      :items="continuum_subset_items"
      :selected.sync="continuum_subset_selected"
      :show_if_single_entry="true"
      :rules="[() => continuum_subset_selected!==spectral_subset_selected || 'Must not match line selection.']"
      label="Continuum"
      api_hint="plg.continuum ="
      :api_hints_enabled="api_hints_enabled"
      hint="Select spectral region that defines the continuum."
    />

    <v-row v-if="continuum_subset_selected=='Surrounding' && spectral_subset_selected!='Entire Spectrum'">
      <!-- DEV NOTE: if changing the validation rules below, also update the logic to clear the results
           in line_analysis.py  -->
      <v-text-field
        :label="api_hints_enabled ? 'plg.continuum_width =' : 'Width'"
        type="number"
        v-model.number="continuum_width"
        step="0.1"
        :rules="[() => continuum_width!=='' || 'This field is required.',
                 () => continuum_width<=10 || 'Width must be <= 10.',
                 () => continuum_width>=1 || 'Width must be >= 1.']"
        hint="Width, relative to the overall line spectral region, to fit the linear continuum (excluding the region containing the line).  If 1, will use endpoints within line region only."
        persistent-hint
      >
      </v-text-field>
    </v-row>

    <v-row justify="end">
      <j-tooltip tooltipcontent="calculate results and add to results table">
        <plugin-action-button
          :results_isolated_to_plugin="true"
          :api_hints_enabled="api_hints_enabled"
          :disabled="continuum_subset_selected===spectral_subset_selected"
          @click="calculate_results">
          {{ api_hints_enabled ?
            'plg.get_results(add_to_table=True)'
            :
            'Calculate'
          }}
        </plugin-action-button>
      </j-tooltip>
    </v-row>

    <div v-if="results_available">
      <j-plugin-section-header>Results</j-plugin-section-header>

      <v-row>
        <j-docs-link>
          See the <j-external-link link='https://specutils.readthedocs.io/en/stable/analysis.html' linktext='specutils docs'></j-external-link> for more details on the available analysis functions.
        </j-docs-link>
      </v-row>

      <div style="display: grid"> <!-- overlay container -->
        <div style="grid-area: 1/1">
          <v-row>
            <v-col cols=6><U>Function</U></v-col>
            <v-col cols=6><U>Result</U></v-col>
          </v-row>
          <v-row
            v-for="item in results"
            :key="item.function">
            <v-col cols=6>
              {{  item.function  }}
              <j-tooltip :tooltipcontent="'specutils '+item.function+' documentation'">
                <a v-bind:href="'https://specutils.readthedocs.io/en/stable/api/specutils.analysis.'+item.function.toLowerCase().replaceAll(' ', '_')+'.html'"
                  target="__blank"
                  style="color: #A75000">
                  <v-icon x-small color="#A75000">mdi-open-in-new</v-icon>
                </a>
              </j-tooltip>
            </v-col>
            <v-col cols=6>
              <span v-if="item.error_msg">{{ item.error_msg }}</span>
              <j-number-uncertainty
                v-else
                :value="item.result"
                :uncertainty="item.uncertainty"
                :unit="item.unit"
                :defaultDigs="8"
              ></j-number-uncertainty>
            </v-col>
          </v-row>
        </div>
        <div v-if="results_computing"
            class="text-center"
            style="grid-area: 1/1;
                    z-index:2;
                    margin-left: -24px;
                    margin-right: -24px;
                    padding-top: 60px;
                    background-color: rgb(0 0 0 / 20%)">
          <v-progress-circular
            indeterminate
            color="spinner"
            size="50"
            width="6"
          ></v-progress-circular>
        </div>

        <j-plugin-section-header>Results History</j-plugin-section-header>
        <jupyter-widget :widget="table_widget"></jupyter-widget>

        <div v-if="line_menu_items.length > 0">
          <j-plugin-section-header>Redshift from Centroid</j-plugin-section-header>
          <v-row>
            <j-docs-link>Assign the centroid reported above to the observed wavelength of a given line and set the resulting redshift.  Lines must be loaded and plotted through the Line Lists plugin first.</j-docs-link>
          </v-row>
          <v-row class="row-no-outside-padding">
            <v-col cols=2>
              <j-tooltip tipid='plugin-line-analysis-sync-identify'>
                <v-btn icon @click="() => sync_identify = !sync_identify" style="margin-top: 14px">
                  <img :class="sync_identify ? 'color-to-accent' : 'invert-if-dark'" :src="sync_identify ? sync_identify_icon_enabled : sync_identify_icon_disabled" width="20"/>
                </v-btn>
              </j-tooltip>
            </v-col>
            <v-col cols=10>
              <v-select
                :menu-props="{ left: true }"
                attach
                :items="line_menu_items"
                item-text="title"
                item-value="value"
                v-model="selected_line"
                label="Line"
                hint="Select reference line."
                persistent-hint
              ></v-select>
            </v-col>
          </v-row>

          <v-row v-if="selected_line">
            <v-text-field
              :value='selected_line_redshift'
              class="mt-0 pt-0"
              type="number"
              label="Redshift"
              hint="Redshift that will be applied by assigning centroid to the selected line."
              persistent-hint
              disabled
            ></v-text-field>
          </v-row>

          <v-row justify="end">
            <j-tooltip tipid='plugin-line-analysis-assign'>
              <v-btn
              color="accent"
              style="padding-left: 8px; padding-right: 8px;"
              text
              :disabled="!selected_line"
              @click="line_assign">
                Assign
              </v-btn>
            </j-tooltip>
          </v-row>
        </div>
      </div>
    </div>
  </j-tray-plugin>
</template>
