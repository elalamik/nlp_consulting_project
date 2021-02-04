import pandas as pd
import numpy as np
import nltk
import json
import os
import logging
from logzero import logger
import logzero

from helpers import unicode_remover, punctuation_remover, character_transformer, contraction_transformer, lemmatize

from nltk.tokenize import word_tokenize
from nltk.corpus import wordnet

from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from wordcloud import WordCloud
from PIL import Image

class Cleaner():

    def __init__(self, stop_words_filename='custom_stop_words.txt', debug=0):
        self.init_stop_words(stop_words_filename)
        self.contraction_filename = 'contractions.json'
        self.tag_dict = {
            "J": wordnet.ADJ,
            "N": wordnet.NOUN,
            "V": wordnet.VERB,
            "R": wordnet.ADV
        }

        # Set logging level
        logzero.loglevel(logging.WARNING)
        if int(debug) == 0 :
            logging.disable(logging.WARNING)


    def init_stop_words(self, stop_words_filename):
        """ Sets custom stop words list """

        delete_from_stop_words = ['more', 'most', 'very',  'no', 'nor', 'not']
        self.stop_words = nltk.corpus.stopwords.words("english")
        self.stop_words = list(set(self.stop_words) - set(delete_from_stop_words))
        with open(stop_words_filename) as stop_words_file:
            lines = [line.rstrip() for line in stop_words_file]
        self.stop_words += lines


    def set_file(self, filename, index_col='review_id', content_col='comment'):
        """ 
        Sets a new file to be cleaned:
            - self.tokenized_corpus: dict{int: review_id, list[str]: tokenized review (cleaned + split)}
            - self.tokenized_corpus_ngram: dict{int: review_id, list[tuple(n * str)]: tokenized review (cleaned + split)}
            - self.tokenized_corpus_sentences = dict{int: restaurant_id, str: tokenized review sentence}
            - self.word_count = dict{int: review_id, dict{str: word, int: count}}
            - self.word_count_by_restaurant = dict{int: restaurant_id, dict{str: word, int: count}}
            - self.df_word_frequency = dict{int: restaurant_id, df(index = review_id, columns = set of vocab per restaurant)}

        Raises:
            TypeError: if filename is not of type str
        """

        if isinstance(filename, str):
            self.filename = filename
            json = pd.read_json(filename, lines=True)
            json.set_index(index_col, inplace = True)
            self.df = json
            self.index_col = index_col
            self.content_col = content_col
            self.tokenized_corpus = {}
            self.tokenized_corpus_ngram = {}
            self.tokenized_corpus_sentences = {}
            self.word_count = {}
            self.word_count_by_restaurant = {}
            self.df_word_frequency = {}
        else:
            raise TypeError("Input types accepted: str")

        self.corpus = dict(zip(self.df.index, self.df[self.content_col]))

    def clean(self, document):
        """ Cleans document (lower char, removes contractions, accents, punctuations, unicode) """
    
        cleaned_document = document.lower()
        cleaned_document = contraction_transformer(cleaned_document, self.contraction_filename)
        cleaned_document = character_transformer(cleaned_document)
        cleaned_document = unicode_remover(cleaned_document)
        cleaned_document = punctuation_remover(cleaned_document)
        return cleaned_document

    def tokenize(self, document, ngram=1):
        """ 
        Tokenizes one document from corpus
        
        Returns: 
                - unigram 
                - word count
                - opt: ngram (if greater than 1)
        """

        tokenized_document = nltk.word_tokenize(document)
        tokenized_document = lemmatize(tokenized_document, self.stop_words, self.tag_dict)
        word_count = Counter(tokenized_document)
        if ngram > 1:
            tokenized_ngram = list(nltk.ngrams(tokenized_document, n=ngram))
            return tokenized_document, word_count, tokenized_ngram
        else:
            return tokenized_document, word_count

    def preprocessing(self, ngram=1, early_stop=False):
        """ Prepocesses corpus of documents (lower case + removes word contractions, accents, unicode char, and punctuation) """

        logger.warn(f' > STARTING PREPROCESSING')

        if not isinstance(ngram, int) or ngram < 1:
            raise ValueError("ngram argument must be strictly positive integer")

        for idx, review in self.corpus.items():

            if idx % 1000 == 0:
                logger.warn(f' > CLEANING AND TOKENAZING REVIEW ({idx})')

            cleaned_review = self.clean(review)
            if ngram > 1:
                self.tokenized_corpus[idx], self.word_count[idx], self.tokenized_corpus_ngram[idx] = self.tokenize(cleaned_review, ngram)
            else:
                self.tokenized_corpus[idx], self.word_count[idx] = self.tokenize(cleaned_review, ngram)

            if early_stop and idx >= 100:
                break
             
    def preprocess_new_file(self, filename, index_col='review_id', content_col='comment', ngram=1):
        """ Resets cleaner object attributes and preprocesses new file """
        
        self.set_file(filename, index_col, content_col)
        self.preprocessing(ngram)

    def group_by_restaurant(self, restaurant_id):
        """ Groups """
        review_ids = self.df[self.df['restaurant_id'] == restaurant_id].index.values
        restaurant_counter = Counter()
        restaurant_corpus, reviews_id_to_ret = [], []
        for review_id in review_ids:
            try:
                restaurant_counter.update(self.word_count[review_id])
                restaurant_corpus.append(" ".join(self.tokenized_corpus[review_id]))
                reviews_id_to_ret.append(review_id)
            except:
                pass
        return restaurant_counter, restaurant_corpus, reviews_id_to_ret

    def get_word_count_by_restaurant(self, cols='restaurant_id'):
        restaurant_list = [int(item) for item in self.df[cols].unique()]
        
        for restaurant_idx in restaurant_list:
            try:
                review_ids = self.df[self.df[cols] == restaurant_idx].index.values
                review_ids = list(review_ids)
                self.word_count_by_restaurant[restaurant_idx], self.tokenized_corpus_sentences[restaurant_idx], reviews_id_to_ret = self.group_by_restaurant(restaurant_idx)
                
                vectorizer = TfidfVectorizer(stop_words='english')
                vect_corpus = vectorizer.fit_transform(self.tokenized_corpus_sentences[restaurant_idx])
                feature_names = np.array(vectorizer.get_feature_names())
                self.df_word_frequency[restaurant_idx] = pd.DataFrame(data=vect_corpus.todense(), index=reviews_id_to_ret, columns=feature_names)
            except:
                pass 
            

    def save_tokenized_corpus(self, directory):
        """ Saves tokenized corpus in json file """
        with open(directory + 'tokenized' + self.filename, 'w') as tokenized_reviews:
            logger.warn(f' > Writing tokenized_reviews.json')
            json.dump(self.tokenized_corpus, tokenized_reviews)

    def save_wordclouds(self, restaurant_ids='all', directory='./cleaned_data/restaurant_wordclouds/'):

        def save_wordcloud(df_tfidf, restaurant_id, directory, capgemini_mask):
            filename = directory + "restaurant_" + str(restaurant_id) + "_word_cloud.png"
            df_tfidf_mean = df_tfidf.mean().sort_values(ascending=False).to_frame(name='tfidf mean')
            dict_words_tfidf = df_tfidf_mean[df_tfidf_mean['tfidf mean'] != 0].to_dict()['tfidf mean']

            wordcloud = WordCloud(height=600, width=800, background_color="white",
                colormap='Blues', max_words=100, mask=capgemini_mask,
                contour_width=0.5, contour_color='lightsteelblue')
            wordcloud.generate_from_frequencies(frequencies=dict_words_tfidf)
            wordcloud.to_file(filename)     

            logger.warn(f' > WRITING {filename}')

        capgemini_mask = np.array(Image.open("./capgemini.jpg"))

        try:
            os.mkdir(directory)
        except OSError:
            logger.warn("OSError: directory already exists")

        if restaurant_ids == 'all':
            for restaurant_id, df_tfidf in self.df_word_frequency.items():
                save_wordcloud(df_tfidf, restaurant_id, directory, capgemini_mask)
                
        else:
            for restaurant_id in restaurant_ids:
                df_tfidf = self.df_word_frequency[restaurant_id]
                save_wordcloud(df_tfidf, restaurant_id, directory, capgemini_mask)


    def write_tfidfs(self, restaurant_ids='all', directory='./cleaned_data/restaurant_word_frequencies/'):
        
        def write_tfidf(df_tfidf, restaurant_id, directory):
            filename = directory + "restaurant_" + str(restaurant_id) + "_word_freq.csv"
            df_tfidf.to_csv(filename)
            logger.warn(f' > WRITING {filename}')

        try:
            os.mkdir(directory)
        except OSError:
            logger.warn("OSError: directory already exists")

        if restaurant_ids == 'all':
            for restaurant_id, df_tfidf in self.df_word_frequency.items():
                write_tfidf(df_tfidf, restaurant_id, directory)
        else:
            for restaurant_id in restaurant_ids:
                df_tfidf = self.df_word_frequency[restaurant_id]
                write_tfidf(df_tfidf, restaurant_id, directory)
                