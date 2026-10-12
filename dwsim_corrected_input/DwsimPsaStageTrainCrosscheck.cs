using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using DWSIM.Automation;
using DWSIM.Interfaces;
using DWSIM.Interfaces.Enums;
using DWSIM.Interfaces.Enums.GraphicObjects;
using DWSIM.Thermodynamics.PropertyPackages;
using DWSIM.Thermodynamics.Streams;
using DWSIM.UnitOperations.UnitOperations;
using DWSIM.UnitOperations.UnitOperations.Auxiliary;

public static class DwsimPsaStageTrainCrosscheck
{
    private static readonly string[] ShortNames = { "H2", "CO", "CO2", "N2", "CH4" };
    private static readonly Dictionary<string, string> DwsimNames = new Dictionary<string, string>
    {
        { "H2", "Hydrogen" },
        { "CO", "Carbon monoxide" },
        { "CO2", "Carbon dioxide" },
        { "N2", "Nitrogen" },
        { "CH4", "Methane" }
    };

    private static string F(double value)
    {
        return value.ToString("G17", CultureInfo.InvariantCulture);
    }

    private static List<Dictionary<string, string>> ReadCsv(string path)
    {
        var lines = File.ReadAllLines(path);
        if (lines.Length < 2) throw new InvalidOperationException("Input deck is empty: " + path);
        var header = lines[0].Split(',');
        var rows = new List<Dictionary<string, string>>();
        for (int i = 1; i < lines.Length; i++)
        {
            if (string.IsNullOrWhiteSpace(lines[i])) continue;
            var values = lines[i].Split(',');
            if (values.Length != header.Length)
                throw new InvalidOperationException("CSV column mismatch at line " + (i + 1));
            var row = new Dictionary<string, string>();
            for (int j = 0; j < header.Length; j++) row[header[j]] = values[j];
            rows.Add(row);
        }
        return rows;
    }

    private static double D(Dictionary<string, string> row, string key)
    {
        return double.Parse(row[key], CultureInfo.InvariantCulture);
    }

    private static MaterialStream AddStream(IFlowsheet flowsheet, PropertyPackage propertyPackage, int x, int y, string tag)
    {
        var stream = flowsheet.AddObject(ObjectType.MaterialStream, x, y, tag) as MaterialStream;
        if (stream == null) throw new InvalidOperationException("Unable to add material stream " + tag);
        stream.PropertyPackage = propertyPackage;
        if (stream.Phases[0].Compounds.Count == 0)
            flowsheet.AddCompoundsToMaterialStream(stream);
        return stream;
    }

    private static T AddUnit<T>(IFlowsheet flowsheet, PropertyPackage propertyPackage, ObjectType type, int x, int y, string tag)
        where T : class, ISimulationObject
    {
        var unit = flowsheet.AddObject(type, x, y, tag) as T;
        if (unit == null) throw new InvalidOperationException("Unable to add unit " + tag);
        unit.PropertyPackage = propertyPackage;
        return unit;
    }

    private static void SetFeed(MaterialStream feed, Dictionary<string, string> row)
    {
        double total = ShortNames.Sum(name => D(row, "feed_" + name + "_mol_s"));
        var composition = new double[feed.Phases[0].Compounds.Count];
        var order = feed.Phases[0].Compounds.Keys.ToList();
        for (int i = 0; i < order.Count; i++)
        {
            var match = DwsimNames.FirstOrDefault(pair => pair.Value == order[i]);
            composition[i] = string.IsNullOrEmpty(match.Key) ? 0.0 : D(row, "feed_" + match.Key + "_mol_s") / total;
        }
        feed.SpecType = StreamSpec.Temperature_and_Pressure;
        feed.SetTemperature(D(row, "temperature_K"));
        feed.SetPressure(D(row, "raw_feed_pressure_Pa"));
        feed.SetMolarFlow(total);
        feed.SetOverallMolarComposition(composition);
    }

    private static void SetSeparatorSpecs(ComponentSeparator separator, Dictionary<string, string> row, string prefix)
    {
        separator.SpecifiedStreamIndex = 0;
        separator.ComponentSepSpecs.Clear();
        foreach (var compound in separator.FlowSheet.SelectedCompounds.Keys)
        {
            string shortName = DwsimNames.FirstOrDefault(pair => pair.Value == compound).Key;
            double fraction = string.IsNullOrEmpty(shortName) ? 0.0 : D(row, prefix + shortName);
            separator.ComponentSepSpecs.Add(
                compound,
                new ComponentSeparationSpec(compound, SeparationSpec.PercentInletMolarFlow, 100.0 * fraction, "%")
            );
        }
    }

    private static double ComponentFlow(MaterialStream stream, string shortName)
    {
        return stream.GetCompoundMolarFlow(DwsimNames[shortName]);
    }

    private static void AppendStreamRows(StringBuilder csv, string caseId, params MaterialStream[] streams)
    {
        foreach (var stream in streams)
        {
            csv.Append(caseId).Append(',').Append(stream.GraphicObject.Tag).Append(',')
                .Append(F(stream.GetTemperature())).Append(',')
                .Append(F(stream.GetPressure())).Append(',')
                .Append(F(stream.GetMolarFlow()));
            foreach (var name in ShortNames)
                csv.Append(',').Append(F(ComponentFlow(stream, name)));
            csv.AppendLine();
        }
    }

    public static string Run(string source, string inputDeck, string resultsCsv, string streamsCsv, string savedCaseDirectory)
    {
        var rows = ReadCsv(inputDeck);
        Directory.CreateDirectory(Path.GetDirectoryName(resultsCsv));
        Directory.CreateDirectory(Path.GetDirectoryName(streamsCsv));
        Directory.CreateDirectory(savedCaseDirectory);

        var automation = new Automation3();
        try
        {
            var flowsheet = automation.LoadFlowsheet2(source);
            if (flowsheet == null) throw new InvalidOperationException("DWSIM returned a null flowsheet.");
            var propertyPackage = flowsheet.PropertyPackages.Values.First() as PropertyPackage;
            if (propertyPackage == null) throw new InvalidOperationException("No property package was found.");

            // The loaded file supplies a fully initialized DWSIM flowsheet, compound
            // database, and property package.  Remove its original unit operations so
            // the saved cross-check cases contain only the PSA polishing train.
            foreach (var existing in flowsheet.SimulationObjects.Values.ToList())
                flowsheet.DeleteSelectedObject(null, EventArgs.Empty, existing.GraphicObject, false, false);
            if (flowsheet.SimulationObjects.Count != 0)
                throw new InvalidOperationException("Unable to clear the DWSIM template flowsheet.");

            var raw = AddStream(flowsheet, propertyPackage, 1800, 100, "QC-RAW");
            var c1Hot = AddStream(flowsheet, propertyPackage, 2000, 100, "QC-C1-HOT");
            var stage1Feed = AddStream(flowsheet, propertyPackage, 2200, 100, "QC-S1-FEED");
            var stage1PermHigh = AddStream(flowsheet, propertyPackage, 2450, 40, "QC-S1-PERM-20BAR");
            var stage1Ret = AddStream(flowsheet, propertyPackage, 2450, 180, "QC-S1-RET");
            var stage1PermLow = AddStream(flowsheet, propertyPackage, 2650, 40, "QC-S1-PERM-1BAR");
            var c2aHot = AddStream(flowsheet, propertyPackage, 2850, 40, "QC-C2A-HOT");
            var c2aCool = AddStream(flowsheet, propertyPackage, 3050, 40, "QC-C2A-COOL");
            var c2bHot = AddStream(flowsheet, propertyPackage, 3250, 40, "QC-C2B-HOT");
            var c2bCool = AddStream(flowsheet, propertyPackage, 3450, 40, "QC-C2B-COOL");
            var c2cHot = AddStream(flowsheet, propertyPackage, 3650, 40, "QC-C2C-HOT");
            var stage2Feed = AddStream(flowsheet, propertyPackage, 3850, 40, "QC-S2-FEED");
            var stage2PermHigh = AddStream(flowsheet, propertyPackage, 4100, 0, "QC-S2-PERM-20BAR");
            var stage2Ret = AddStream(flowsheet, propertyPackage, 4100, 120, "QC-S2-RET");
            var product = AddStream(flowsheet, propertyPackage, 4300, 0, "QC-PRODUCT-1BAR");

            var c1 = AddUnit<Compressor>(flowsheet, propertyPackage, ObjectType.Compressor, 1900, 100, "QC-C1");
            var cooler1 = AddUnit<Cooler>(flowsheet, propertyPackage, ObjectType.Cooler, 2100, 100, "QC-E1");
            var separator1 = AddUnit<ComponentSeparator>(flowsheet, propertyPackage, ObjectType.ComponentSeparator, 2350, 100, "QC-POLYMER");
            var valve1 = AddUnit<Valve>(flowsheet, propertyPackage, ObjectType.Valve, 2550, 40, "QC-V1");
            var c2a = AddUnit<Compressor>(flowsheet, propertyPackage, ObjectType.Compressor, 2750, 40, "QC-C2A");
            var cooler2a = AddUnit<Cooler>(flowsheet, propertyPackage, ObjectType.Cooler, 2950, 40, "QC-E2A");
            var c2b = AddUnit<Compressor>(flowsheet, propertyPackage, ObjectType.Compressor, 3150, 40, "QC-C2B");
            var cooler2b = AddUnit<Cooler>(flowsheet, propertyPackage, ObjectType.Cooler, 3350, 40, "QC-E2B");
            var c2c = AddUnit<Compressor>(flowsheet, propertyPackage, ObjectType.Compressor, 3550, 40, "QC-C2C");
            var cooler2c = AddUnit<Cooler>(flowsheet, propertyPackage, ObjectType.Cooler, 3750, 40, "QC-E2C");
            var separator2 = AddUnit<ComponentSeparator>(flowsheet, propertyPackage, ObjectType.ComponentSeparator, 4000, 40, "QC-PD");
            var valve2 = AddUnit<Valve>(flowsheet, propertyPackage, ObjectType.Valve, 4200, 0, "QC-V2");

            flowsheet.ConnectObjects(raw.GraphicObject, c1.GraphicObject, 0, 0);
            flowsheet.ConnectObjects(c1.GraphicObject, c1Hot.GraphicObject, 0, 0);
            flowsheet.ConnectObjects(c1Hot.GraphicObject, cooler1.GraphicObject, 0, 0);
            flowsheet.ConnectObjects(cooler1.GraphicObject, stage1Feed.GraphicObject, 0, 0);
            flowsheet.ConnectObjects(stage1Feed.GraphicObject, separator1.GraphicObject, 0, 0);
            flowsheet.ConnectObjects(separator1.GraphicObject, stage1PermHigh.GraphicObject, 0, 0);
            flowsheet.ConnectObjects(separator1.GraphicObject, stage1Ret.GraphicObject, 1, 0);
            flowsheet.ConnectObjects(stage1PermHigh.GraphicObject, valve1.GraphicObject, 0, 0);
            flowsheet.ConnectObjects(valve1.GraphicObject, stage1PermLow.GraphicObject, 0, 0);
            flowsheet.ConnectObjects(stage1PermLow.GraphicObject, c2a.GraphicObject, 0, 0);
            flowsheet.ConnectObjects(c2a.GraphicObject, c2aHot.GraphicObject, 0, 0);
            flowsheet.ConnectObjects(c2aHot.GraphicObject, cooler2a.GraphicObject, 0, 0);
            flowsheet.ConnectObjects(cooler2a.GraphicObject, c2aCool.GraphicObject, 0, 0);
            flowsheet.ConnectObjects(c2aCool.GraphicObject, c2b.GraphicObject, 0, 0);
            flowsheet.ConnectObjects(c2b.GraphicObject, c2bHot.GraphicObject, 0, 0);
            flowsheet.ConnectObjects(c2bHot.GraphicObject, cooler2b.GraphicObject, 0, 0);
            flowsheet.ConnectObjects(cooler2b.GraphicObject, c2bCool.GraphicObject, 0, 0);
            flowsheet.ConnectObjects(c2bCool.GraphicObject, c2c.GraphicObject, 0, 0);
            flowsheet.ConnectObjects(c2c.GraphicObject, c2cHot.GraphicObject, 0, 0);
            flowsheet.ConnectObjects(c2cHot.GraphicObject, cooler2c.GraphicObject, 0, 0);
            flowsheet.ConnectObjects(cooler2c.GraphicObject, stage2Feed.GraphicObject, 0, 0);
            flowsheet.ConnectObjects(stage2Feed.GraphicObject, separator2.GraphicObject, 0, 0);
            flowsheet.ConnectObjects(separator2.GraphicObject, stage2PermHigh.GraphicObject, 0, 0);
            flowsheet.ConnectObjects(separator2.GraphicObject, stage2Ret.GraphicObject, 1, 0);
            flowsheet.ConnectObjects(stage2PermHigh.GraphicObject, valve2.GraphicObject, 0, 0);
            flowsheet.ConnectObjects(valve2.GraphicObject, product.GraphicObject, 0, 0);

            c1.CalcMode = Compressor.CalculationMode.OutletPressure;
            c2a.CalcMode = Compressor.CalculationMode.OutletPressure;
            c2b.CalcMode = Compressor.CalculationMode.OutletPressure;
            c2c.CalcMode = Compressor.CalculationMode.OutletPressure;
            c1.AdiabaticEfficiency = 72.0;
            c2a.AdiabaticEfficiency = 72.0;
            c2b.AdiabaticEfficiency = 72.0;
            c2c.AdiabaticEfficiency = 72.0;
            cooler1.CalcMode = Cooler.CalculationMode.OutletTemperature;
            cooler2a.CalcMode = Cooler.CalculationMode.OutletTemperature;
            cooler2b.CalcMode = Cooler.CalculationMode.OutletTemperature;
            cooler2c.CalcMode = Cooler.CalculationMode.OutletTemperature;
            cooler1.DeltaP = 0.0;
            cooler2a.DeltaP = 0.0;
            cooler2b.DeltaP = 0.0;
            cooler2c.DeltaP = 0.0;
            valve1.CalcMode = Valve.CalculationMode.OutletPressure;
            valve2.CalcMode = Valve.CalculationMode.OutletPressure;

            var result = new StringBuilder();
            result.Append("validation_kind,case_id,calculation_errors,property_package,raw_molar_flow_mol_s,")
                .Append("c1_power_W,c2a_power_W,c2b_power_W,c2c_power_W,c2_total_power_W,total_adiabatic_compression_power_W,python_isothermal_compression_power_W,power_ratio_adiabatic_to_isothermal,")
                .Append("cooler1_duty_W,cooler2_total_duty_W,total_cooling_duty_W,c1_hot_temperature_K,c2a_hot_temperature_K,c2b_hot_temperature_K,c2c_hot_temperature_K,c2_max_hot_temperature_K,")
                .Append("stage1_feed_pressure_Pa,stage1_permeate_pressure_Pa,stage2_feed_pressure_Pa,product_pressure_Pa,")
                .Append("stage1_balance_max_abs_mol_s,stage2_balance_max_abs_mol_s,product_reference_max_abs_mol_s,")
                .Append("product_h2_fraction,product_co_ppm,product_co2_ppm,product_n2_ppm,product_ch4_ppm")
                .AppendLine();
            var streamResult = new StringBuilder();
            streamResult.Append("case_id,stream,temperature_K,pressure_Pa,total_molar_flow_mol_s,h2_mol_s,co_mol_s,co2_mol_s,n2_mol_s,ch4_mol_s").AppendLine();

            int successful = 0;
            double maximumBalance = 0.0;
            double maximumProductDifference = 0.0;
            double maximumPowerRatio = 0.0;
            double maximumAdiabaticPower = 0.0;
            foreach (var row in rows)
            {
                SetFeed(raw, row);
                double outletPressure = D(row, "membrane_feed_pressure_Pa");
                double permeatePressure = D(row, "permeate_pressure_Pa");
                double temperature = D(row, "temperature_K");
                double stageRatio = Math.Pow(outletPressure / permeatePressure, 1.0 / 3.0);
                c1.POut = outletPressure;
                c2a.POut = permeatePressure * stageRatio;
                c2b.POut = permeatePressure * stageRatio * stageRatio;
                c2c.POut = outletPressure;
                cooler1.OutletTemperature = temperature;
                cooler2a.OutletTemperature = temperature;
                cooler2b.OutletTemperature = temperature;
                cooler2c.OutletTemperature = temperature;
                valve1.OutletPressure = permeatePressure;
                valve2.OutletPressure = permeatePressure;
                SetSeparatorSpecs(separator1, row, "stage1_permeate_fraction_");
                SetSeparatorSpecs(separator2, row, "stage2_permeate_fraction_");
                flowsheet.ResetCalculationStatus();

                var errors = automation.CalculateFlowsheet4(flowsheet);
                string caseId = row["case_id"];
                if (errors.Count > 0)
                {
                    throw new InvalidOperationException(
                        "DWSIM errors for " + caseId + ": " + string.Join(" | ", errors.Select(e => e.ToString()).ToArray())
                    );
                }

                double stage1Balance = 0.0;
                double stage2Balance = 0.0;
                double productDifference = 0.0;
                foreach (var name in ShortNames)
                {
                    stage1Balance = Math.Max(stage1Balance, Math.Abs(
                        ComponentFlow(stage1Feed, name) - ComponentFlow(stage1PermHigh, name) - ComponentFlow(stage1Ret, name)
                    ));
                    stage2Balance = Math.Max(stage2Balance, Math.Abs(
                        ComponentFlow(stage2Feed, name) - ComponentFlow(stage2PermHigh, name) - ComponentFlow(stage2Ret, name)
                    ));
                    productDifference = Math.Max(productDifference, Math.Abs(
                        ComponentFlow(product, name) - D(row, "python_product_" + name + "_mol_s")
                    ));
                }
                double c1PowerW = 1000.0 * Math.Abs(c1.DeltaQ);
                double c2aPowerW = 1000.0 * Math.Abs(c2a.DeltaQ);
                double c2bPowerW = 1000.0 * Math.Abs(c2b.DeltaQ);
                double c2cPowerW = 1000.0 * Math.Abs(c2c.DeltaQ);
                double c2PowerW = c2aPowerW + c2bPowerW + c2cPowerW;
                double totalPowerW = c1PowerW + c2PowerW;
                double pythonPowerW = D(row, "python_isothermal_compression_power_W");
                double powerRatio = totalPowerW / pythonPowerW;
                double cooler1W = 1000.0 * Math.Abs(cooler1.DeltaQ.GetValueOrDefault());
                double cooler2W = 1000.0 * (
                    Math.Abs(cooler2a.DeltaQ.GetValueOrDefault()) +
                    Math.Abs(cooler2b.DeltaQ.GetValueOrDefault()) +
                    Math.Abs(cooler2c.DeltaQ.GetValueOrDefault())
                );
                double c2MaximumTemperature = Math.Max(c2aHot.GetTemperature(), Math.Max(c2bHot.GetTemperature(), c2cHot.GetTemperature()));
                double productTotal = product.GetMolarFlow();

                result.Append(row["validation_kind"]).Append(',').Append(caseId).Append(",0,")
                    .Append(propertyPackage.ComponentName).Append(',')
                    .Append(F(raw.GetMolarFlow())).Append(',')
                    .Append(F(c1PowerW)).Append(',').Append(F(c2aPowerW)).Append(',').Append(F(c2bPowerW)).Append(',')
                    .Append(F(c2cPowerW)).Append(',').Append(F(c2PowerW)).Append(',').Append(F(totalPowerW)).Append(',')
                    .Append(F(pythonPowerW)).Append(',').Append(F(powerRatio)).Append(',')
                    .Append(F(cooler1W)).Append(',').Append(F(cooler2W)).Append(',').Append(F(cooler1W + cooler2W)).Append(',')
                    .Append(F(c1Hot.GetTemperature())).Append(',').Append(F(c2aHot.GetTemperature())).Append(',')
                    .Append(F(c2bHot.GetTemperature())).Append(',').Append(F(c2cHot.GetTemperature())).Append(',')
                    .Append(F(c2MaximumTemperature)).Append(',')
                    .Append(F(stage1Feed.GetPressure())).Append(',').Append(F(stage1PermLow.GetPressure())).Append(',')
                    .Append(F(stage2Feed.GetPressure())).Append(',').Append(F(product.GetPressure())).Append(',')
                    .Append(F(stage1Balance)).Append(',').Append(F(stage2Balance)).Append(',').Append(F(productDifference)).Append(',')
                    .Append(F(ComponentFlow(product, "H2") / productTotal)).Append(',')
                    .Append(F(1.0e6 * ComponentFlow(product, "CO") / productTotal)).Append(',')
                    .Append(F(1.0e6 * ComponentFlow(product, "CO2") / productTotal)).Append(',')
                    .Append(F(1.0e6 * ComponentFlow(product, "N2") / productTotal)).Append(',')
                    .Append(F(1.0e6 * ComponentFlow(product, "CH4") / productTotal)).AppendLine();

                AppendStreamRows(streamResult, caseId, raw, c1Hot, stage1Feed, stage1PermLow, c2aHot, c2aCool, c2bHot, c2bCool, c2cHot, stage2Feed, product, stage1Ret, stage2Ret);
                maximumBalance = Math.Max(maximumBalance, Math.Max(stage1Balance, stage2Balance));
                maximumProductDifference = Math.Max(maximumProductDifference, productDifference);
                maximumPowerRatio = Math.Max(maximumPowerRatio, powerRatio);
                maximumAdiabaticPower = Math.Max(maximumAdiabaticPower, totalPowerW);
                successful++;

                if (caseId == "corner_02" || caseId == "corner_06")
                {
                    string savePath = Path.Combine(savedCaseDirectory, "PSA_STAGE_TRAIN_" + caseId + ".dwxmz");
                    automation.SaveFlowsheet(flowsheet, savePath, true);
                }
            }

            File.WriteAllText(resultsCsv, result.ToString(), new UTF8Encoding(false));
            File.WriteAllText(streamsCsv, streamResult.ToString(), new UTF8Encoding(false));
            return "DWSIM_VERSION=" + automation.GetVersion() + Environment.NewLine +
                   "PROPERTY_PACKAGE=" + propertyPackage.ComponentName + Environment.NewLine +
                   "CASES_OK=" + successful + "/" + rows.Count + Environment.NewLine +
                   "MAX_COMPONENT_BALANCE_MOL_S=" + F(maximumBalance) + Environment.NewLine +
                   "MAX_PRODUCT_REFERENCE_DIFFERENCE_MOL_S=" + F(maximumProductDifference) + Environment.NewLine +
                   "MAX_ADIABATIC_COMPRESSION_POWER_W=" + F(maximumAdiabaticPower) + Environment.NewLine +
                   "MAX_ADIABATIC_TO_ISOTHERMAL_POWER_RATIO=" + F(maximumPowerRatio);
        }
        finally
        {
            automation.ReleaseResources();
        }
    }
}
