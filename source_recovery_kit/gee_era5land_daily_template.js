// ERA5-Land DAILY_AGGR independently reconstructed extraction (NOT recovered original).
// Built by generate_gee_script.py from the author's PROVISIONAL station coordinates.
// Dataset docs: https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_DAILY_AGGR
// Explicit UTC labels: do not silently shift dates to Bangladesh local observation dates.

var DATASET_ID = 'ECMWF/ERA5_LAND/DAILY_AGGR';
var PIXEL_SCALE_METRES = 11132;
var EXPORT_FOLDER = 'ERA5_BMD_recovery';
// 'sample' queues THREE small public-BMD-bulletin windows; 'annual' queues 24 yearly exports.
// Do NOT change to annual until sample coordinates/date/unit checks are accepted.
var RUN_MODE = 'sample';
var YEAR_START = 2000;
var YEAR_END = 2023;
var SAMPLE_CASES = [
  {label: '20190511', start: '2019-05-06', end: '2019-05-16', points: ['S24']},
  {label: '20210520', start: '2021-05-15', end: '2021-05-25', points: ['S05', 'S15', 'S34']},
  {label: '20230906', start: '2023-09-01', end: '2023-09-11', points: ['S12', 'S20', 'S26']}
];

var STATION_POINTS = __POINTS_JS__;
var allStations = ee.FeatureCollection(STATION_POINTS.map(function(s) {
  return ee.Feature(ee.Geometry.Point([s.lon, s.lat]), {
    point_id: s.point_id,
    station_name: s.station_name,
    station_lat_provisional: s.lat,
    station_lon_provisional: s.lon,
    coordinate_status: 'author_draft_unverified_historical'
  });
}));

// Each source name and its native unit verified against the GEE collection docs.
var SOURCE_BANDS = [
  'temperature_2m', 'temperature_2m_max', 'temperature_2m_min',
  'dewpoint_temperature_2m', 'total_precipitation_sum',
  'volumetric_soil_water_layer_1', 'volumetric_soil_water_layer_2',
  'surface_solar_radiation_downwards_sum', 'potential_evaporation_sum',
  'total_evaporation_sum', 'u_component_of_wind_10m',
  'v_component_of_wind_10m', 'surface_pressure'
];
var RAW_OUTPUT_BANDS = [
  't2m_K', 'tmax_K', 'tmin_K', 'd2m_K', 'rain_m',
  'swvl1_m3m3', 'swvl2_m3m3', 'ssrd_Jm2', 'pet_signed_m',
  'aet_signed_m', 'u10_ms', 'v10_ms', 'sp_Pa'
];
var EXTRA_OUTPUT_BANDS = [
  't2m_C', 'tmax_C', 'tmin_C', 'd2m_C', 'rain_mm_raw', 'rain_mm_clipped',
  'ssrd_MJ_m2_day', 'pet_signed_mm', 'aet_signed_mm',
  'pet_evap_positive_mm', 'aet_evap_positive_mm', 'sp_kPa'
];
var SELECTORS = [
  'point_id', 'station_name', 'date_utc', 'gee_image_id',
  'station_lat_provisional', 'station_lon_provisional', 'coordinate_status'
].concat(RAW_OUTPUT_BANDS).concat(EXTRA_OUTPUT_BANDS);

function makeComparableBands(sourceImage) {
  var x = ee.Image(sourceImage).select(SOURCE_BANDS, RAW_OUTPUT_BANDS);
  var extra = ee.Image.cat([
    x.select('t2m_K').subtract(273.15).rename('t2m_C'),
    x.select('tmax_K').subtract(273.15).rename('tmax_C'),
    x.select('tmin_K').subtract(273.15).rename('tmin_C'),
    x.select('d2m_K').subtract(273.15).rename('d2m_C'),
    x.select('rain_m').multiply(1000).rename('rain_mm_raw'),
    x.select('rain_m').max(ee.Image.constant(0)).multiply(1000).rename('rain_mm_clipped'),
    x.select('ssrd_Jm2').divide(1000000).rename('ssrd_MJ_m2_day'),
    x.select('pet_signed_m').multiply(1000).rename('pet_signed_mm'),
    x.select('aet_signed_m').multiply(1000).rename('aet_signed_mm'),
    x.select('pet_signed_m').multiply(-1000).rename('pet_evap_positive_mm'),
    x.select('aet_signed_m').multiply(-1000).rename('aet_evap_positive_mm'),
    x.select('sp_Pa').divide(1000).rename('sp_kPa')
  ]);
  return x.addBands(extra);
}

function collectDays(startUTC, endExclusiveUTC, stationFeatures) {
  var collection = ee.ImageCollection(DATASET_ID).filterDate(startUTC, endExclusiveUTC);
  var n = collection.size();
  var days = collection.toList(n);
  // ee.List.map (not ImageCollection.map) is important: map returns FeatureCollections.
  var dayCollections = ee.List.sequence(0, n.subtract(1)).map(function(idx) {
    var img = ee.Image(days.get(idx));
    var mapped = makeComparableBands(img);
    var day = ee.Date(img.get('system:time_start')).format('YYYY-MM-dd', 'UTC');
    var imageId = ee.String(img.get('system:index'));
    return mapped.reduceRegions({
      collection: stationFeatures,
      reducer: ee.Reducer.first(),
      scale: PIXEL_SCALE_METRES,
      tileScale: 4
    }).map(function(f) {
      return f.set({'date_utc': day, 'gee_image_id': imageId});
    });
  });
  return ee.FeatureCollection(dayCollections).flatten();
}

print('Source', DATASET_ID);
print('Coordinate warning: 2000–2023 site moves NOT verified.');
print('Time warning: GEE DAILY_AGGR dates are UTC and precipitation sums are m.');
print('Station point count', allStations.size());

if (RUN_MODE === 'sample') {
  SAMPLE_CASES.forEach(function(test) {
    var sampleSites = allStations.filter(ee.Filter.inList('point_id', test.points));
    var sampleRows = collectDays(test.start, test.end, sampleSites);
    print('Sample ' + test.label + ' first 8 rows', sampleRows.limit(8));
    Export.table.toDrive({
      collection: sampleRows,
      description: 'ERA5_BMD_sample_' + test.label + '_UTC',
      folder: EXPORT_FOLDER,
      fileFormat: 'CSV',
      selectors: SELECTORS
    });
  });
} else if (RUN_MODE === 'annual') {
  for (var year = YEAR_START; year <= YEAR_END; year++) {
    var start = year + '-01-01';
    var end = (year + 1) + '-01-01';
    Export.table.toDrive({
      collection: collectDays(start, end, allStations),
      description: 'ERA5_BMD_all36_' + year + '_UTC',
      folder: EXPORT_FOLDER,
      fileFormat: 'CSV',
      selectors: SELECTORS
    });
  }
} else {
  throw new Error('RUN_MODE must be sample or annual');
}
