# Trip Advisor Scraping Tool

Session 1: Scraping (Capgemini Data Camp)

Tool to scrap Trip Advisor UK website (https://www.tripadvisor.co.uk/) for restaurants and their associated reviews made by different users.

# Setup

```
pip install -r requirements.txt
```

# Run from Command Line

```
scrapy crawl RestoReviewSpider -a directory='./scraped_data/' -a root_url='user_chosen_url' -a debug=0 -a maxpage_resto=3 -a maxpage_reviews=50 -a scrap_user=0 -a scrap_website_menu=0
```

-a option allows for command line input arguments with scrapy command
* directory: directory of user defined data folder for scraped reviews, restaurants and users information
* debug: 0 or 1, for no debug information or with debug information respectively
* root_url: root url for list of restaurants (URL of city chosen by user)
* maxpage_resto: number of pages of restaurants to parse from base URL (1 page = ~35 restaurants)
* maxpage_reviews: number of pages of reviews to parse for given restaurant (1 page = 10 reviews)
* scrap_user: 0 or 1, for not returning user information (quicker) or returning user information respectively.
* scrap_website_menu: 0 or 1, for not scraping restaurants' website and menu

# Data Collected (JSON format)

* Restaurant Information: Restaurant Id (unique) name, number of reviews, price, cuisine type, address, phone number, website, menu, ranking, rating
* Review Information: Id (unique), Restaurant Id, Username, date of visit, rating, title, comment
* User Information: Username (unique), date joined, number of contributions, number of followers, number of following
