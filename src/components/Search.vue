<template>
  <div class="fixed-top fixed-offset pt-3 pb-2">
    <div class="container">
      <div class="form-row d-flex align-items-center">
        <div class="col-9">
          <input type="text" placeholder="Filter elements" class="form-control"
                 v-bind:value="filter" v-on:input="debounceInput"/>
        </div>
        <div class="col-3 text-right">
          <span>{{ resultsCount }} of {{ totalCount }} elements displayed.</span>
        </div>
      </div>
      <div>
        <small class="form-text text-muted">
          We use <a href="https://lunrjs.com/guides/searching.html">lunr syntax</a>, please use wildcards (*) to search inside a URI, e.g. *dataset*.
        </small>
      </div>
    </div>
  </div>
</template>

<script>
  import _ from 'lodash'

  export default {
    props: ['filter', 'resultsCount', 'totalCount'],
    methods: {
      debounceInput: _.debounce(function(e) {
        this.$emit('update-filter', e.target.value)
      }, 500)
    }
  }
</script>

<style>
.fixed-offset {
  top: 56px;
  background-color: white;
  border-bottom: 1px solid silver;
}
</style>