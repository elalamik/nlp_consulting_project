import pandas as pd
import numpy as np
import nltk
import json
import logging
from logzero import logger

from helpers import unicode_remover, punctuation_remover, character_transformer, contraction_transformer, lemmatize_and_delete_stop_words

from nltk.tokenize import word_tokenize
from nltk.corpus import wordnet

from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer

class Cleaner():

    def __init__(self, stop_words_filename='custom_stop_words.txt', contraction_filename='contractions.json'):
        self.init_stop_words(stop_words_filename)
        self.contraction_filename = contraction_filename
        self.tag_dict = {
            "J": wordnet.ADJ,
            "N": wordnet.NOUN,
            "V": wordnet.VERB,
            "R": wordnet.ADV
        }


    def init_stop_words(self, stop_words_filename='custom_stop_words.txt'):

        delete_from_stop_words = ['more', 'most', 'very',  'no', 'nor', 'not', "didn't"]
        self.stop_words = nltk.corpus.stopwords.words("english")
        self.stop_words = list(set(self.stop_words) - set(delete_from_stop_words))
        with open(stop_words_filename) as stop_words_file:
            lines = [line.rstrip() for line in stop_words_file]
        self.stop_words += lines
        logger.warn(' STOP WORDS ({})'.format(self.stop_words))


    def set_file(self, filename, index_col='review_id', content_col='comment'):
        
        """ Sets a new file to be cleaned:
            - self.tokenized_corpus: dict{int: review_id, list[str]: tokenized review (cleaned + split)}
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
            self.tokenized_corpus_sentences = {}
            self.word_count = {}
            self.word_count_by_restaurant = {}
            self.df_word_frequency = {}
        else:
            raise TypeError("Input types accepted: str")

        self.corpus = dict(zip(self.df.index, self.df[self.content_col]))

    
    def tokenize_on_steroids(self, document, ngram=1):

        if not isinstance(ngram, int):
            raise TypeError("ngram argument must be int")
        if ngram >= 1:
            tokenized_document = nltk.word_tokenize(document)
            tokenized_document, word_count = lemmatize_and_delete_stop_words(tokenized_document, self.stop_words, self.tag_dict)
            if ngram > 1:
                tokenized_document = list(nltk.ngrams(tokenized_document, n=ngram))
        else:
            raise ValueError("ngram argument must be strictly positive")
        return tokenized_document, word_count

    def clean(self, ngram=1):

        for idx, review in self.corpus.items():

            logger.warn(f' > TOKENAZING REVIEW ({idx})')

            cleaned_review = review.lower()
            cleaned_review = contraction_transformer(cleaned_review, self.contraction_filename)
            cleaned_review = character_transformer(cleaned_review)
            cleaned_review = unicode_remover(cleaned_review)
            cleaned_review = punctuation_remover(cleaned_review)
            
            self.tokenized_corpus[idx], self.word_count[idx] = self.tokenize_on_steroids(cleaned_review, ngram)

            # if idx >= 100:
            #     break
        

    def clean_new_file(self, filename, index_col='review_id', 
                    content_col='comment', contraction_filename='contractions.json'):

        self.set_file_info(filename, index_col, 
                    content_col, contraction_filename)
        self.clean()

    def group_by_restaurant(self, restaurant_id):
                
        review_ids = self.df[self.df['restaurant_id'] == restaurant_id].index.values
        restaurant_counter = Counter()
        restaurant_corpus = []
        for review_id in review_ids:
            try:
                restaurant_counter.update(self.word_count[review_id])
                restaurant_corpus.append(" ".join(self.tokenized_corpus[review_id]))
            except:
                pass
        return restaurant_counter, restaurant_corpus

    def get_word_count_by_restaurant(self, cols='restaurant_id'):
        restaurant_list = self.df[cols].unique()

        for restaurant_idx in restaurant_list:
            try:
                review_ids = self.df[self.df[cols] == restaurant_idx].index.values
                self.word_count_by_restaurant[restaurant_idx], self.tokenized_corpus_sentences[restaurant_idx] = self.group_by_restaurant(restaurant_idx)
                vectorizer = TfidfVectorizer(stop_words='english')
                vect_corpus = vectorizer.fit_transform(self.tokenized_corpus_sentences[restaurant_idx])
                feature_names = np.array(vectorizer.get_feature_names())
                self.df_word_frequency[restaurant_idx] = pd.DataFrame(data=vect_corpus.todense(), index=review_ids, columns=feature_names)
            except:
                pass

            

    def write_file(self):

        with open('tokenized_reviews.json', 'w') as tokenized_reviews:
            json.dump(self.tokenized_corpus, tokenized_reviews)

        with open('word_frequency.json', 'w') as word_frequency:
            json.dump(self.df_word_frequency, word_frequency)