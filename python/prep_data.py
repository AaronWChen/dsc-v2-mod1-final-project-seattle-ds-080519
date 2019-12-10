import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import sklearn.metrics as metrics
from geopy import distance
import joblib


def create_train_test_df(ran_state=50):
  raw_data = pd.read_csv("../raw_data/kc_house_data.csv")

  X_train, X_test, y_train, y_test = train_test_split(raw_data.drop('price', axis=1), 
                                                    raw_data['price'],
                                                   random_state=ran_state,
                                                   stratify=raw_data['zipcode'])
  return X_train, X_test, y_train, y_test


def clean_df(X_df):
  unwanted = ['id', 'date', 'condition', 'sqft_above', 'sqft_basement', 
              'yr_renovated', 'sqft_living15', 'sqft_lot15']
  drop = X_df.drop(unwanted, axis=1)
  drop = drop[drop['bedrooms'] != 33]
  cleaned_df = drop.fillna(0)
  return cleaned_df


def distance_calc(cleaned_df):
  cleaned_df['lat_and_long'] = list(zip(cleaned_df['lat'], cleaned_df['long']))

  bellevue_lat_long = (47.61002, -122.18785)
  seattle_lat_long = (47.6062, -122.3321)
  airport_lat_long = (47.4502, -122.3088)
  snoq_falls_lat_long = (47.5417, -121.8377)
  vancouver_lat_long = (49.2827, -123.1207)
  mt_rain_lat_long = (46.8523, -121.7603)
  oly_lat_long = (47.8021, -123.6044)
  tacoma_lat_long = (47.2529, -122.4443)
  stevens_lat_long = (47.7448, -121.0890)

  bellevue_dists = [distance.distance(elem,bellevue_lat_long).miles for elem in cleaned_df['lat_and_long']]
  cleaned_df['dist_from_bellevue'] = bellevue_dists

  seattle_dists = [distance.distance(elem, seattle_lat_long).miles for elem in cleaned_df['lat_and_long']]
  cleaned_df['dist_from_seattle'] = seattle_dists
  
  seatac_dists = [distance.distance(elem, airport_lat_long).miles for elem in cleaned_df['lat_and_long']]
  cleaned_df['dist_from_seatac'] = seatac_dists
  
  snoq_falls_dists = [distance.distance(elem, snoq_falls_lat_long).miles for elem in cleaned_df['lat_and_long']]
  cleaned_df['dist_from_snoq'] = snoq_falls_dists
  
  vanc_dists = [distance.distance(elem, vancouver_lat_long).miles for elem in cleaned_df['lat_and_long']]
  cleaned_df['dist_from_vanc'] = vanc_dists
  
  mt_rain_dists = [distance.distance(elem, mt_rain_lat_long).miles for elem in cleaned_df['lat_and_long']]
  cleaned_df['dist_from_vanc'] = mt_rain_dists
  
  oly_dists = [distance.distance(elem, oly_lat_long).miles for elem in cleaned_df['lat_and_long']]
  cleaned_df['dist_from_oly'] = oly_dists
  
  tacoma_dists = [distance.distance(elem, tacoma_lat_long).miles for elem in cleaned_df['lat_and_long']]
  cleaned_df['dist_from_tacoma'] = tacoma_dists
  
  stevens_dists = [distance.distance(elem, stevens_lat_long).miles for elem in cleaned_df['lat_and_long']]
  cleaned_df['dist_from_stevens'] = stevens_dists

  distance_df = cleaned_df.copy()
  return distance_df


def generate_hybrid_data(distance_df):
  # Use the natural log of livable square footage instead of the 
  # normal value in order to preserve linear relationship between
  # the natural log of the price and the livablesquare footage
  distance_df['sqft_living'] = np.log(distance_df['sqft_living'])

  # Create a column where the number of bedrooms is multiplied
  # by the number of bathrooms
  distance_df['beds_and_baths'] = np.log(distance_df['bedrooms'] * distance_df['bathrooms'])

  # Create a column from the natural log of the square of the livable square footage
  distance_df['squared_living'] = np.log(np.square(distance_df['sqft_living']))

  # Create a column from the natural log of livable square footage divided by the number of bedrooms
  distance_df['sqft_per_bedroom'] = np.log(distance_df['sqft_living']/distance_df['bedrooms'])

  # Create a column from the distances from both downtown Seattle and SeaTac airport
  distance_df['dist_seatac_seattle'] = (distance_df['dist_from_seatac'] + distance_df['dist_from_seattle'])/2

  # Create a column from the distances from both downtown Bellevue and SeaTac airport
  distance_df['dist_seatac_bellevue'] = (distance_df['dist_from_seatac'] + distance_df['dist_from_bellevue'])/2

  # Create a column from the square of the distance from SeaTac
  distance_df['square_dist_seatac'] = np.square(distance_df['dist_from_seatac'])

  # Create a column from the square of the distance from Bellevue
  distance_df['square_seatac_bellevue'] = np.square(distance_df['dist_seatac_bellevue'])

  # Create a column from the natural log of the livable square footage times assessor grade
  distance_df['sqft_times_grade'] = np.log(distance_df['sqft_living'] * distance_df['grade'])

  # Create a column using 1 + the waterfront boolean times the livable square footage
  # and then taking the natural log of that product
  # 1 is added to prevent a zero from showing up in the calculation of natural log
  distance_df['water_weight'] = np.log((1+distance_df['waterfront']) * distance_df['sqft_living'])

  # Create a column using 1 + the assessor's view rating times the livable square footage
  # and then taking the natural log of that product
  # 1 is added to prevent a zero from showing up in the calculation of natural log
  distance_df['view_weight'] = np.log((1+distance_df['view']) * distance_df['sqft_living'])

  hybridized = distance_df.drop(['lat', 'long', 'lat_and_long'], axis=1).copy()
  
  return hybridized


def fit_transform_standard_scale(hybridized):
  ss = StandardScaler()
  to_ss = hybridized.drop('zipcode', axis=1)
  ss.fit(to_ss)
  scaled = ss.transform(to_ss)
  scaled = pd.DataFrame(scaled, columns = to_ss.columns, index= to_ss.index)
  combined = pd.concat([scaled, hybridized['zipcode'].reindex(scaled.index)], 
                        axis=1)
  return ss, combined


def transform_standard_scale(ss, X_test):
  to_ss = X_test.drop('zipcode', axis=1)
  X_test_sc = ss.transform(to_ss)
  X_test_sc = pd.DataFrame(X_test_sc, columns= to_ss.columns, index=to_ss.index)
  test_combined = pd.concat([X_test_sc, X_test['zipcode'].reindex(X_test_sc.index)],
                            axis=1)
  return test_combined


def fit_transform_one_hot_encode_zipcodes(scaled):
  ohe = OneHotEncoder(drop='first', categories='auto')
  to_ohe = scaled['zipcode']
  price_zip_trans = ohe.fit_transform(to_ohe.values.reshape(-1,1))
  zip_sparse = pd.DataFrame(price_zip_trans.todense(), columns=ohe.get_feature_names())
  scaled.drop(['zipcode'], axis=1, inplace=True)
  ohe_df = zip_sparse.join(scaled, how='inner')
  return ohe, ohe_df


def transform_ohe(ohe, scaled):
  to_ohe = scaled['zipcode']
  price_zip_trans = ohe.transform(to_ohe.values.reshape(-1,1))
  zip_sparse = pd.DataFrame(price_zip_trans.todense(), columns=ohe.get_feature_names())
  scaled.drop(['zipcode'], axis=1, inplace=True)
  ohe_trans = zip_sparse.join(scaled, how='inner')
  return ohe_trans


def make_joblibs(rand_state=50):
  X_train, X_test, y_train, y_test = create_train_test_df(rand_state)

  with open(f"joblib/test_subset_rand_state_{rand_state}.joblib", 
            "wb") as fo:
    joblib.dump(X_test, fo, compress=True)

  with open(f"joblib/test_subset_targets_rand_state_{rand_state}.joblib", 
            "wb") as fo:
    joblib.dump(y_test, fo, compress=True)

  clean = clean_df(X_train)
  dist = distance_calc(clean)
  hybrid = generate_hybrid_data(dist)
  ss, scaled = fit_transform_standard_scale(hybrid)
  ohe, one_hot = fit_transform_one_hot_encode_zipcodes(scaled)
  log_train_prices = np.log(y_train)

  with open(f"joblib/standard_scaler_rand_state_{rand_state}.joblib", 
            "wb") as fo:
    joblib.dump(ss, fo, compress=True)

  with open(f"joblib/ohe_rand_state_{rand_state}.joblib", 
            "wb") as fo:
    joblib.dump(ohe, fo, compress=True)

  with open(f"joblib/prepped_training_set_rand_state_{rand_state}.joblib", 
            "wb") as fo:
    joblib.dump(one_hot, fo, compress=True)

  with open(f"joblib/log_train_prices_rand_state_{rand_state}.joblib",
            "wb") as fo:
    joblib.dump(log_train_prices, fo, compress=True)

  clean_test = clean_df(X_test)
  dist_test = distance_calc(clean_test)
  hybrid_test = generate_hybrid_data(dist_test)
  scaled_test = transform_standard_scale(ss, hybrid_test)
  one_hot_test = transform_ohe(ohe, scaled_test)
  log_test_prices = np.log(y_test)

  with open(f"joblib/prepped_test_set_rand_state_{rand_state}.joblib", 
            "wb") as fo:
    joblib.dump(one_hot_test, fo, compress=True)

  with open(f"joblib/log_test_prices_rand_state_{rand_state}.joblib",
            "wb") as fo:
    joblib.dump(log_test_prices, fo, compress=True)

make_joblibs()