# TripAdvisor reviews cleaner

## Run from Command Line

```
python3 main.py --files [filenames] --debug --early_stop int
```

Usage:
* --files [filenames]: provide the paths to all the files to be processed
* --debug: displays intermediary logs
* --early_stop int: stops the cleaning process after reaching the given review_id

## Run Exploratory Data Analysis from Jupyter Notebook

On Jupyter Notebook, execute the cells in the file ``` EDA.ipynb ```


## Data Available on Git

The folder ``` cleaned_data ``` contains the output computed from running ``` python3 main.py ``` on raw data available in the folder ``` ../scraper ```.
* The sub-folder ``` cleaned_data/restaurant_word_frequencies ``` contains files named ``` restaurant_ + restaurant_id + _word_freq.csv ``` according to the restaurant ids defined in the ```restaurant.json``` table from the ``` ../scraper ``` folder. These files contain dataframes formatted as follows:
  * as rows the review_ids from the table ``` reviews.json ``` from the ``` ../scraper ``` folder for this restaurant
  * as columns the unique words found in all the reviews for this restaurant
* The sub-folder ``` cleaned_data/restaurant_wordclouds ``` contains files named ``` restaurant_ + restaurant_id + _wordcloud.png ``` according to the restaurant ids defined in the ```restaurant.json``` table from the ``` ../scraper ``` folder. These are image files computed with the library ``` WordCloud ``` showing the most frequent words found in the reviews for a given restaurant
* The file ``` cleaned_data/tokenized_reviews.json ``` contains the tokenized reviews formatted as follows:
  * as key, the ```review_id``` from the table ``` reviews.json ``` from the ``` ../scraper ``` folder
  * as value, a list of strings containing each tokenized word for the given review.
