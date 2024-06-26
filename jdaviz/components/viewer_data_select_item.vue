<template>
  <div style="display: contents">
    <div v-if="is_wcs_only">
      <j-tooltip
        :tooltipcontent="isRefData() ? 'Current viewer orientation' : 'Set as viewer orientation'"
        span_style="width: 36px"
      >
        <v-btn 
          icon
          :color="isRefData() ? 'accent' : 'default'"
          @click="selectRefData">
            <v-icon>{{isRefData() ? "mdi-radiobox-marked" : "mdi-radiobox-blank"}}</v-icon>
        </v-btn>
      </j-tooltip>
    </div>
    <div v-else-if="isChild(item) && !parentIsVisible(item)">
      <j-tooltip
        :tooltipcontent="'Select parent data first to make this layer visible'"
        span_style="width: 36px;"
      >
        <v-btn
          icon
          color="default"
          style="cursor: default;"
          >
            <v-icon>mdi-checkbox-blank-off-outline</v-icon>
        </v-btn>
      </j-tooltip>
    </div>
    <div v-else-if="isSelected">
      <j-tooltip :tipid="multi_select ? 'viewer-data-select' : 'viewer-data-radio'">
        <v-btn 
          icon
          :color="visibleState==='visible' ? 'accent' : 'default'"
          @click="selectClicked">
            <v-icon v-if="multi_select || item.type==='trace'">{{visibleState!=='hidden' ? "mdi-checkbox-marked" : "mdi-checkbox-blank-outline"}}</v-icon>
            <v-icon v-else>{{visibleState!=='hidden' ? "mdi-radiobox-marked" : "mdi-radiobox-blank"}}</v-icon>
        </v-btn>
      </j-tooltip>
    </div>
    <div v-else-if="!linkedByWcs() || item.has_wcs || item.is_astrowidgets_markers_table">
      <j-tooltip tipid="viewer-data-enable">
        <v-btn
          icon
          color="default"
          @click="selectClicked">
            <v-icon>mdi-plus</v-icon>
        </v-btn>
      </j-tooltip>
    </div>
    <div v-else>
      <j-tooltip tipid="viewer-data-nowcs">
        <v-btn
          icon
          color="default"
          disabled>
          <v-icon>mdi-plus</v-icon>
        </v-btn>
      </j-tooltip>
    </div>
    <j-tooltip :tooltipcontent="is_wcs_only ? '' : 'data label: '+item.name" span_style="font-size: 12pt; padding-top: 6px; padding-left: 4px; padding-right: 16px; width: calc(100% - 80px); white-space: nowrap; cursor: default;">
      <j-layer-viewer-icon span_style="margin-left: 4px;" :icon="icon" :icons="icons" color="#000000DE"></j-layer-viewer-icon>

      <div class="text-ellipsis-middle" style="font-weight: 500;">
        <span>
          {{itemNamePrefix}}
        </span>
        <span>
          {{itemNameExtension}}
        </span>
      </div>
    </j-tooltip>

    <div v-if="isSelected && isUnloadable" style="padding-left: 2px; right: 2px">
      <j-tooltip tipid='viewer-data-disable'>
        <v-btn
          icon
          @click="$emit('data-item-unload', {
            id: viewer.id,
            item_id: item.id
          })"
        ><v-icon>mdi-close</v-icon></v-btn>
      </j-tooltip>
    </div>

    <div v-if="isDeletable" style="padding-left: 2px; right: 2px">
      <j-tooltip :tipid="is_wcs_only ? 'viewer-wcs-delete' : 'viewer-data-delete'">
        <v-btn
          icon
          @click="$emit('data-item-remove', {item_name: item.name, viewer_id: viewer.id})"
        ><v-icon>mdi-delete</v-icon></v-btn>
      </j-tooltip>
    </div>
  </div>
</template>

<script>

module.exports = {
  props: ['item', 'icon', 'icons', 'multi_select', 'viewer', 'n_data_entries', 'is_wcs_only'],
  methods: {
    selectClicked() {
      prevVisibleState = this.visibleState
      // checkboxes control VISIBILITY of layers not loaded state
      // if we just loaded the data, its probably already visible, but we'll still make sure all
      // appropriate layers are visible and properly handle replace for non-multiselect
      // NOTE: replace=True will exclude removing trace items
      this.$emit('data-item-visibility', {
        id: this.$props.viewer.id,
        item_id: this.$props.item.id,
        visible: prevVisibleState != 'visible' || (!this.multi_select && this.$props.item.type !== 'trace'),
        replace: !this.multi_select && this.$props.item.type !== 'trace'
      })
    },
    selectRefData() {
      if (this.linkedByWcs() && !this.isRefData() && this.is_wcs_only) {
        this.$emit('change-reference-data', {
          id: this.$props.viewer.id,
          item_id: this.$props.item.id
        })
      }
    },
    isRefData() {
      return this.$props.viewer.reference_data_label == this.$props.item.name
    },
    linkedByWcs() {
      return this.$props.viewer.linked_by_wcs
    },
    isChild(item) {
      // only override multi_select choice when data entry is a child:
      return item.parent !== null
    },
    parentIsVisible(item) {
      return this.$props.viewer.selected_data_items[item.parent] === 'visible'
    },
  },
  computed: {
    itemNamePrefix() {
      if (this.$props.item.name.indexOf("[") !== -1) {
        // return everything BEFORE the LAST [
        return this.$props.item.name.split('[').slice(0, -1).join()
      } else {
        return this.$props.item.name
      }
    },
    itemNameExtension() {
      if (this.$props.item.name.indexOf("[") !== -1) {
        // return the LAST [ and everything FOLLOWING
        return '[' + this.$props.item.name.split('[').slice(-1)
      } else {
        return ''
      }
    },
    isSelected() {
      return Object.keys(this.$props.viewer.selected_data_items).includes(this.$props.item.id)
    },
    visibleState() {
      return this.$props.viewer.selected_data_items[this.$props.item.id] || 'hidden'
    },
    isUnloadable() {
      if (this.$props.item.meta.Plugin !== undefined) {
        // (almost) always allow unloading plugin exports
        if (this.$props.viewer.config === 'specviz2d' && this.$props.item.name === 'Spectrum 1D') {
          // the "Spectrum 1D" object is auto-generated from a plugin, but since its the default
          // reference data, we don't want to allow unloading it
          return false
        }
        return true
      }
      if (this.$props.viewer.config === 'cubeviz') {
        // forbid unloading the original reference cube
        // this logic might need to be generalized if supporting custom data labels
        // per-cube or renaming data labels
        const extension = this.itemNameExtension
        if (this.$props.viewer.reference === 'flux-viewer') {
          return ['SCI', 'FLUX'].indexOf(extension) !== -1
        } else if (this.$props.viewer.reference === 'uncert-viewer') {
          return ['IVAR', 'ERR'].indexOf(extension) !== -1
        } else if (this.$props.viewer.reference === 'mask-viewer') {
          return ['MASK', 'DQ'].indexOf(extension) !== -1
        }
      } else if (this.$props.viewer.config === 'specviz2d') {
        if (this.$props.viewer.reference === 'spectrum-2d-viewer') {
          return this.$props.item.name !== 'Spectrum 2D'
        } else if (this.$props.viewer.reference === 'spectrum-viewer') {
          return this.$props.item.name !== 'Spectrum 1D'
        }
      }
      return true
    },
    isDeletable() {
      isLastDataset = (this.$props.n_data_entries <= 1)
      notSelected = !this.isSelected
      isMosviz = this.$props.viewer.config === 'mosviz'
      isCubeviz = this.$props.viewer.config === 'cubeviz'
      isPluginData = !(this.$props.item.meta.Plugin === undefined)
      return notSelected && (isPluginData || (!isLastDataset && !isMosviz && !isCubeviz)) && (this.$props.item.name !== 'Default orientation')
    },
    selectTipId() {
      if (this.multi_select) {
        return 'viewer-data-select'
      } else {
        return 'viewer-data-radio'
      }
    },
    labelColor() {
      if (this.isSelected) {
        return 'black'
      } else {
        return 'gray'
      }
    },
  }
};
</script>

<style>
  .text-ellipsis-middle {
    display: inline-flex;
    flex-wrap: nowrap;
    max-width: 100%;
  }

  .text-ellipsis-middle > span:first-child {
    flex: 0 1 auto;
    text-overflow: ellipsis;
    overflow:hidden;
    white-space:nowrap;
  }

  .text-ellipsis-middle > span + span {
    flex: 1 0 auto;
    white-space: nowrap;
  }
</style>
