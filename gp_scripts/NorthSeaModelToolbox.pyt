import arcpy
import ns
DEBUG = True

class Toolbox(object):
    
    def __init__(self):
        self.label = "NorthSeaModelToolbox"
        self.alias = "NorthSeaModelToolbox"

        # List of tool classes associated with this toolbox
        self.tools = [NorthSeaModel]

class NorthSeaModel(object):
    
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "NorthSeaModel"
        self.description = "North sea windfarm model."
        self.canRunInBackground = False
        
    def getParameterInfo(self):
      inputs = arcpy.Parameter(
        displayName="AllInputs",
        name="AllInputs",
        datatype="Feature Class",
        parameterType="Required",
        multiValue=True,
        direction="Input" )



      resultCode = arcpy.Parameter(
        displayName="ResultCode",
        name="ResultCode",
        datatype="Long",
        parameterType="Derived",
        direction="Output" )

      resultMsg = arcpy.Parameter(
        displayName="ResultMsg",
        name="ResultMsg",
        datatype="String",
        parameterType="Derived",
        direction="Output" )

      sketch_output = arcpy.Parameter(
        displayName="Sketches",
        name="Sketches",
        datatype="Feature Class",
        parameterType="Derived",
        multiValue=True,
        direction="Output" )

      collection_output = arcpy.Parameter(
        displayName="Collection",
        name="Collection",
        datatype="Feature Class",
        parameterType="Derived",
        multiValue=True,
        direction="Output" )
      params = [inputs, resultCode, resultMsg, sketch_output, collection_output]

      return params
    
    def updateParameters(self, parameters):
        return



    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True


    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def depthCost(self, d,baseCost):
        if 25 < abs(d)  < 30:
            return (baseCost/100*10)+baseCost
        if 30 <= abs(d)  < 40:
            return (baseCost/100*20)+baseCost
        if 40 <= abs(d)  < 50:
            return (baseCost/100*30)+baseCost
        if 50 <= abs(d) < 60:
            return (baseCost/100*40)+baseCost
        if abs(d) >= 60:
            return (baseCost/100*50)+baseCost
        else:
            return baseCost

    def execute(self, parameters, messages):
        
        all_inputs = parameters[0].values
        returnCode = "0"
        returnMsg = ""
        wattsM      = 3                                                                     # estimated power production per m^2
        powerReq    = 2100                                                                  # required total power to be met by the plan (MW)
        plantCost   = 600                                                                   # balance of plant cost of all components bar the turbines (substations, cables etc) (million euros) "https://www.thecrownestate.co.uk/media/5408/ei-a-guide-to-an-offshore-wind-farm.pdf"
        turbCost    = 7       
        sketchCounter = 1
        try:
            arcpy.env.overwriteOutput = True
            
            #web mercator projection
            northsea_sr = arcpy.SpatialReference(32631)

            power_hubs_indicative = r"proposed_windfarm_analysis.gdb\power_hubs_indicative_utm31n"

            # Process: Near
            #arcpy.Near_analysis(power_hubs_indicative, "", "NO_LOCATION", "NO_ANGLE", "PLANAR")
            bathy_lyr = r"proposed_windfarm_analysis.gdb\bathy_extract_utm31n"
                # initialise a list to store results for individual sketches
            compositeResult = []

            # Local variables:
            for i, feat in enumerate(all_inputs):    
                #project it to the northsea for accurate area
                rep_in = ns.reproject(feat, northsea_sr, i, "ns_repro"+str(i))
                sketch_id =ns.get_sketch_id(rep_in)

                #zoal stats for each sketch to find mean depth
                sketch_zonal_stats = r"in_memory\table_{}".format(i)
                arcpy.sa.ZonalStatisticsAsTable(rep_in, "NAME", bathy_lyr, sketch_zonal_stats, "DATA", "ALL")
                with arcpy.da.SearchCursor(sketch_zonal_stats, ["*"]) as cursor:
                    arcpy.AddMessage("cursor.fields:: {}".format(cursor.fields))
                    for row in cursor:
                        arcpy.AddMessage("-->{}".format(row))

                # Process: Alter Field
                arcpy.AlterField_management(sketch_zonal_stats, "MEAN", "mean_depth", "Mean depth", "", "8", "NON_NULLABLE", "false")
    
                sketch_points = r"in_memory\sketch_points_{}".format(i)
                arcpy.FeatureToPoint_management(rep_in, sketch_points, "CENTROID")


                sketch_near_table = r"in_memory\near_table_{}".format(i)
                arcpy.GenerateNearTable_analysis(sketch_points, power_hubs_indicative, sketch_near_table, "")
                arcpy.AddMessage("done with near table a analysis")
                
                #copy mean depth and area from zonal stats
                arcpy.JoinField_management(sketch_near_table, "IN_FID", sketch_zonal_stats, "OBJECTID", "mean_depth;AREA;NAME")


                # initialise variables to sum up results for individual sketches
                planTotalCost   = 0
                planArea        = 0
                planProduction  = 0
                planTurbines    = 0
                planDepth       = 0

                fields = ["mean_depth", "IN_FID", "NEAR_DIST", "AREA", "NAME"]
                with arcpy.da.SearchCursor(sketch_near_table, fields) as cursor:
                    for row in cursor:
                        
                        depth = row[0]
                        in_fid = row[1]
                        dist = row[2]
                        area = row[3]
                        sketch_id = row[4]
                        arcpy.AddMessage("------------->>>area is {}".format(area))

                        areaCovered = int(math.ceil(area/1000000))          # division is to convert from m^2 to km^2
                        numTurbines = int(math.ceil(area/1200000))          # division is how many m^2 a turbine requires
                        meanDepth = int(abs(depth))
                        production = (int(area)*3) /1000000                 # division is to convert to megawatts
                        cableCost =  int(math.ceil((dist*160)/1000000))     # rounds result up to million euros
                        baseCost = numTurbines*turbCost                     # see turbCost variable (line28)
                        depthAdjust = self.depthCost(depth,baseCost)-baseCost    # see depthCost function line 38
                        totalCost = baseCost+depthAdjust

                        compositeResult.append([sketchCounter,areaCovered,numTurbines,meanDepth,production,cableCost,baseCost,depthAdjust,totalCost, sketch_id])

                        
                        planTotalCost += totalCost                          # sum various values throughout the loop iterations
                        planArea += area
                        planProduction += production
                        planTurbines += numTurbines
                        planDepth += depthAdjust

                        # increment the sketchCounter
                        sketchCounter += 1

                        planTotalCost += (sketchCounter-1)*plantCost  

            sketchRS = self.writeResults(compositeResult, "comp_results")
            collectionRS = self.writeTotalResults(planTotalCost, planArea, planProduction, planTurbines, planDepth, sketchCounter, "total_results")
        
            if DEBUG:
                arcpy.AddMessage(arcpy.Describe(sketchRS).pjson)
                arcpy.AddMessage(arcpy.Describe(collectionRS).pjson)
            
            arcpy.SetParameter(1, returnCode)            
            arcpy.SetParameter(2, returnMsg)
            arcpy.SetParameter(3, sketchRS)
            arcpy.SetParameter(4, collectionRS)


        except StandardError, e:
            arcpy.AddError(e)
            arcpy.SetParameter(1, -1)            
            arcpy.SetParameter(2, "Error running windfarm model: {}".format(e))
            arcpy.SetParameter(3, [])
            arcpy.SetParameter(4, [])
        return

    def writeResults(self, compositeResult, table_name):
        #sketchCounter,areaCovered,numTurbines,meanDepth,production,cableCost,baseCost,depthAdjust,totalCost
        cols = [ "CNTR", "AREA_COV", "NUM_TURB", "MEAN_DEPTH", "PROD", "CABLE_CST", "BASE_CST", "DEPTH_ADJ", "TOT_CST", "NAME"]
        result_table = ns.create_inmemory_text_table(table_name, cols)
        with arcpy.da.InsertCursor(result_table, cols) as cursor:
            for res in compositeResult:
                cursor.insertRow([res[0], res[1], res[2], res[3], res[4], res[5], res[6], res[7], res[8], res[9]])

        rs = arcpy.RecordSet()
        rs.load(result_table)
        return rs

    def writeTotalResults(self, planTotalCost, planArea, planProduction, planTurbines, planDepth, sketchCounter, table_name):
        #sketchCounter,areaCovered,numTurbines,meanDepth,production,cableCost,baseCost,depthAdjust,totalCost
        cols = ["TOT_CST", "AREA", "PROD", "NUM_TURB", "DEPTH", "NUM_SKETCH"]
        result_table = ns.create_inmemory_text_table(table_name, cols)
        with arcpy.da.InsertCursor(result_table, cols) as cursor:
            cursor.insertRow([planTotalCost, planArea, planProduction, planTurbines, planDepth, sketchCounter])

        rs = arcpy.RecordSet()
        rs.load(result_table)
        return rs
