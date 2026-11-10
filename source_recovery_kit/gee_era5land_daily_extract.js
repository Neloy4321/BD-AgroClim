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

var STATION_POINTS = [
  {
    "point_id": "S01",
    "station_name": "Ambagan (Ctg)",
    "lat": 22.36,
    "lon": 91.79
  },
  {
    "point_id": "S02",
    "station_name": "Barisal",
    "lat": 22.75,
    "lon": 90.3667
  },
  {
    "point_id": "S03",
    "station_name": "Bhola",
    "lat": 22.68,
    "lon": 90.65
  },
  {
    "point_id": "S04",
    "station_name": "Bogra",
    "lat": 24.85,
    "lon": 89.37
  },
  {
    "point_id": "S05",
    "station_name": "Chandpur",
    "lat": 23.23,
    "lon": 90.7
  },
  {
    "point_id": "S06",
    "station_name": "Chittagong",
    "lat": 22.27,
    "lon": 91.82
  },
  {
    "point_id": "S07",
    "station_name": "Chuadanga",
    "lat": 23.65,
    "lon": 88.82
  },
  {
    "point_id": "S08",
    "station_name": "Comilla",
    "lat": 23.43,
    "lon": 91.18
  },
  {
    "point_id": "S09",
    "station_name": "Cox's Bazar",
    "lat": 21.45,
    "lon": 91.97
  },
  {
    "point_id": "S10",
    "station_name": "Dhaka",
    "lat": 23.7667,
    "lon": 90.3833
  },
  {
    "point_id": "S11",
    "station_name": "Dinajpur",
    "lat": 25.65,
    "lon": 88.68
  },
  {
    "point_id": "S12",
    "station_name": "Faridpur",
    "lat": 23.6,
    "lon": 89.85
  },
  {
    "point_id": "S13",
    "station_name": "Feni",
    "lat": 23.03,
    "lon": 91.42
  },
  {
    "point_id": "S14",
    "station_name": "Gazipur",
    "lat": 24.0,
    "lon": 90.42
  },
  {
    "point_id": "S15",
    "station_name": "Hatiya",
    "lat": 22.43,
    "lon": 91.1
  },
  {
    "point_id": "S16",
    "station_name": "Ishurdi",
    "lat": 24.13,
    "lon": 89.05
  },
  {
    "point_id": "S17",
    "station_name": "Jashore",
    "lat": 23.18,
    "lon": 89.17
  },
  {
    "point_id": "S18",
    "station_name": "Khepupara",
    "lat": 21.98,
    "lon": 90.23
  },
  {
    "point_id": "S19",
    "station_name": "Khulna",
    "lat": 22.78,
    "lon": 89.53
  },
  {
    "point_id": "S20",
    "station_name": "Kutubdia",
    "lat": 21.82,
    "lon": 91.85
  },
  {
    "point_id": "S21",
    "station_name": "Madaripur",
    "lat": 23.17,
    "lon": 90.2
  },
  {
    "point_id": "S22",
    "station_name": "Maijdee Court",
    "lat": 22.87,
    "lon": 91.1
  },
  {
    "point_id": "S23",
    "station_name": "Mongla",
    "lat": 22.47,
    "lon": 89.6
  },
  {
    "point_id": "S24",
    "station_name": "Mymensingh",
    "lat": 24.72,
    "lon": 90.42
  },
  {
    "point_id": "S25",
    "station_name": "Patuakhali",
    "lat": 22.33,
    "lon": 90.33
  },
  {
    "point_id": "S26",
    "station_name": "Rajshahi",
    "lat": 24.37,
    "lon": 88.7
  },
  {
    "point_id": "S27",
    "station_name": "Rangamati",
    "lat": 22.53,
    "lon": 92.2
  },
  {
    "point_id": "S28",
    "station_name": "Rangpur",
    "lat": 25.73,
    "lon": 89.23
  },
  {
    "point_id": "S29",
    "station_name": "Saidpur",
    "lat": 25.75,
    "lon": 88.92
  },
  {
    "point_id": "S30",
    "station_name": "Sandwip",
    "lat": 22.48,
    "lon": 91.43
  },
  {
    "point_id": "S31",
    "station_name": "Satkhira",
    "lat": 22.72,
    "lon": 89.08
  },
  {
    "point_id": "S32",
    "station_name": "Sitakunda",
    "lat": 22.63,
    "lon": 91.7
  },
  {
    "point_id": "S33",
    "station_name": "Srimangal",
    "lat": 24.3,
    "lon": 91.73
  },
  {
    "point_id": "S34",
    "station_name": "Sylhet",
    "lat": 24.9,
    "lon": 91.88
  },
  {
    "point_id": "S35",
    "station_name": "Tangail",
    "lat": 24.25,
    "lon": 89.92
  },
  {
    "point_id": "S36",
    "station_name": "Teknaf",
    "lat": 20.87,
    "lon": 92.3
  }
];
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
