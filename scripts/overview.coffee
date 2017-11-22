ReportTab = require 'reportTab'
templates = require '../templates/templates.js'
_partials = require '../node_modules/seasketch-reporting-api/templates/templates.js'

partials = []
for key, val of _partials
  partials[key.replace('node_modules/seasketch-reporting-api/', '')] = val
d3=window.d3

class OverviewTab extends ReportTab
  name: 'Overview'
  className: 'overview'
  template: templates.overview
  dependencies: [
    'NorthSeaModel'
  ]
  render: () ->
    returnMsg = @recordSet('NorthSeaModel', 'ResultMsg')
    

    # pull data from GP script
    sketches = @recordSet('NorthSeaModel', 'Sketches').toArray()
    collection = @recordSet('NorthSeaModel', 'Collection').toArray()
    if collection?.length > 0
      whole_plan = collection[0]
      @updateWholePlan whole_plan

    installation_cost = @addCommas((whole_plan.NUM_SKETCH)*600)

    base_cost = @updateSketches sketches
    # setup context object with data and render the template from it
    context =
      sketch: @model.forTemplate()
      sketchClass: @sketchClass.forTemplate()
      attributes: @model.getAttributes()
      admin: @project.isAdmin window.user
      sketches: sketches
      whole_plan: whole_plan
      installation_cost:installation_cost
      base_cost: base_cost
    
    @$el.html @template.render(context, templates)

  updateWholePlan: (whole_plan) =>
    whole_plan.AREA = @addCommas Math.ceil(parseFloat(whole_plan.AREA)/1000000.0)
    whole_plan.NUM_TURB = @addCommas whole_plan.NUM_TURB
    whole_plan.NUM_SKETCH = whole_plan.NUM_SKETCH
    whole_plan.PROD = @addCommas whole_plan.PROD
    whole_plan.DEPTH_CST = @addCommas Math.ceil(whole_plan.DEPTH_CST/10)*10
    whole_plan.TOT_CST = @addCommas Math.ceil(whole_plan.TOT_CST/10)*10
    whole_plan.BASE_CST = @addCommas Math.ceil(whole_plan.BASE_CST/10)*10
    whole_plan.ZONE_CST = @addCommas Math.ceil(whole_plan.ZONE_CST/10)*10

  updateSketches: (sketches) =>
    base_cost = 0.0
    for sketch in sketches
      base_cost = base_cost+parseInt(sketch.BASE_CST)
      sketch.AREA_COV = @addCommas sketch.AREA_COV
      sketch.NUM_TURB = @addCommas sketch.NUM_TURB
      sketch.MEAN_DEPTH = @addCommas sketch.MEAN_DEPTH
      sketch.BASE_CST = @addCommas Math.ceil(sketch.BASE_CST/10)*10
      sketch.TOT_CST = @addCommas Math.ceil(sketch.TOT_CST/10)*10
      sketch.DEPTH_ADJ = @addCommas sketch.DEPTH_ADJ
      sketch.DIST_CST = @addCommas Math.ceil(sketch.DIST_CST/10)*10
      

    return @addCommas Math.ceil(base_cost/10)*10

  addCommas: (num_str) =>
    num_str += ''
    x = num_str.split('.')
    x1 = x[0]
    x2 = if x.length > 1 then '.' + x[1] else ''
    rgx = /(\d+)(\d{3})/
    while rgx.test(x1)
      x1 = x1.replace(rgx, '$1' + '.' + '$2')
    return x1 + x2

module.exports = OverviewTab