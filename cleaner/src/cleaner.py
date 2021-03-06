import pandas as pd
import numpy as np
import nltk
import json
import os
import logging
import logzero
from logzero import logger

from helpers import unicode_remover, character_remover, character_transformer, contraction_transformer, lemmatize

from nltk.tokenize import word_tokenize
from nltk.corpus import wordnet

from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from PIL import Image

class Cleaner():

    def __init__(self, stop_words_filename='custom_stop_words.txt', debug=False, early_stop=None):
        
        assets_directory = 'assets/'
        self.init_stop_words(assets_directory + stop_words_filename)
        self.contraction_filename = assets_directory + 'contractions.json'
        self.early_stop = early_stop
        self.tag_dict = {
            "J": wordnet.ADJ,
            "N": wordnet.NOUN,
            "V": wordnet.VERB,
            "R": wordnet.ADV
        }

        # Set logging level
        logzero.loglevel(logging.WARNING)
        if debug is False :
            logging.disable(logging.WARNING)


    def init_stop_words(self, stop_words_filename):
        """ Sets custom stop words list """

        delete_from_stop_words = ['more', 'most', 'very',  'no', 'nor', 'not']
        self.stop_words = nltk.corpus.stopwords.words("english")
        self.stop_words = list(set(self.stop_words) - set(delete_from_stop_words))
        with open(stop_words_filename) as stop_words_file:
            lines = [line.rstrip() for line in stop_words_file]
        self.stop_words += lines


    def set_file(self, filepath, index_col='review_id', content_col='comment'):
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

        if isinstance(filepath, str):
            self.filename = filepath.split('/')[-1]
            json = pd.read_json(filepath, lines=True)
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
        """ Cleans document (lower case + removes word contractions, accents, unicode char, and punctuation) """
    
        cleaned_document = document.lower()
        cleaned_document = contraction_transformer(cleaned_document, self.contraction_filename)
        cleaned_document = character_transformer(cleaned_document)
        cleaned_document = unicode_remover(cleaned_document)
        cleaned_document = character_remover(cleaned_document)
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


    def preprocessing(self, ngram=1):
        """ Prepocesses corpus of documents by cleaning, tokenizing, and word count per document """

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

            if self.early_stop is not None and idx >= self.early_stop:
                logger.warn(f' > EARLY STOPPING AT IDX ({idx})')
                break

        self.compute_restaurant_tfidf()

    def group_by_restaurant(self, restaurant_id):
        """ Sets tokenized corpus per restaurant and computes associated word count """

        review_ids = self.df[self.df['restaurant_id'] == restaurant_id].index.values
        restaurant_counter = Counter()
        restaurant_corpus, tokenized_reviews = [], []

        for review_id in review_ids:
            try:
                restaurant_counter.update(self.word_count[review_id])
                restaurant_corpus.append(" ".join(self.tokenized_corpus[review_id]))
                tokenized_reviews.append(review_id)
            except:
                pass
        return restaurant_counter, restaurant_corpus, tokenized_reviews


    def compute_restaurant_tfidf(self, col='restaurant_id'):
        """ Computes TF-IDF Matrix of reviews per restaurant """

        restaurant_list = [int(element) for element in self.df[col].unique()]
        
        for restaurant_idx in restaurant_list:
            try:
                self.word_count_by_restaurant[restaurant_idx], self.tokenized_corpus_sentences[restaurant_idx], tokenized_reviews = self.group_by_restaurant(restaurant_idx)
                vectorizer = TfidfVectorizer(stop_words='english')
                vect_corpus = vectorizer.fit_transform(self.tokenized_corpus_sentences[restaurant_idx])
                feature_names = np.array(vectorizer.get_feature_names())
                self.df_word_frequency[restaurant_idx] = pd.DataFrame(data=vect_corpus.todense(), index=tokenized_reviews, columns=feature_names)
            except:
                pass
            

    def save_tokenized_corpus(self, directory):
        """ Saves tokenized corpus in json file """
        
        try:
            os.mkdir(directory)
        except OSError:
            logger.warn("OSError: directory already exists")
            
        with open((directory + 'tokenized_' + self.filename), 'w') as tokenized_reviews:
            logger.warn(f' > Writing tokenized_{self.filename}')
            json.dump(self.tokenized_corpus, tokenized_reviews)


    def save_files(self, directory, callable_name, restaurant_ids='all', mask_path=None):
        """ Saves files (Wordclouds or TF-IDF) for corpora """
        
        logger.warn(f' > SAVING {callable_name.__name__[5:]} FILES ')

        try:
            os.mkdir(directory)
        except OSError:
            logger.warn("OSError: directory already exists")
        
        try:
            mask = np.array(Image.open(mask_path))
        except:
            mask = None

        if restaurant_ids == 'all':
            for restaurant_id, df in self.df_word_frequency.items():
                callable_name(df, restaurant_id, directory, mask)
        else:
            for restaurant_id in list(restaurant_ids):
                df = self.df_word_frequency[restaurant_id]
                callable_name(df, restaurant_id, directory, mask)