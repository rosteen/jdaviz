<template>
  <div @mouseover="show_dataset_selected = true" @mouseleave="show_dataset_selected = false" style="min-width: 300px">
    <div v-if="icon" style="position: absolute; height: 100%">
      <v-toolbar-items>
        <v-btn icon tile>
          <j-layer-viewer-icon :icon="icon" color="white" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
        </v-btn>
        <span style="display: inline-block; white-space: nowrap; line-height: 14pt; margin: 0; position: absolute; margin-left: 48px">
          <table>
            <tr>
              <td colspan="4" :style="row1_unreliable ? 'color: #B8B8B8' : ''">
                <b>{{ row1a_title }} </b>{{ row1a_text }}&nbsp;&nbsp;
                <b>{{ row1b_title }} </b>{{ row1b_text }}
              </td>
            </tr>
            <tr :style="row2_unreliable ? 'color: #B8B8B8' : ''">
              <td width="42"><b>{{ row2_title }}</b></td>
              <td>{{ row2_text }}</td>
            </tr>
            <tr :style="row3_unreliable ? 'color: #B8B8B8' : ''">
              <td width="42"><b>{{ row3_title }}</b></td>
              <td>{{ row3_text }}</td>
            </tr>
          </table>
        </span>
      </v-toolbar-items>
    </div>
    <div v-else style="position: absolute; height: 100%">
      <v-toolbar-items>
        <j-tooltip tipid='coords-info-cycle'>
          <v-btn icon tile @click="next_layer()">
            <j-layer-viewer-icon :icon="dataset_icon" color="white" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
          </v-btn>
        </j-tooltip>
        <span v-if="show_dataset_selected" style="padding-top: 22px">
          {{dataset_selected}}
        </span>
      </v-toolbar-items>
    </div>
</div>
</template>

<script>
  module.exports = {
    data: function () {
      return {
        show_dataset_selected: false,
      }
    },
  }
</script>
