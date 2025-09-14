import tweepy
import requests
import json
import os
import logging
from datetime import datetime, timedelta, timezone

# Set up logging
logging.basicConfig(filename="spacex_bot.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.info("Script started")

# X API credentials (use environment variables from GitHub secrets)
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")

# Authenticate with X API v2
try:
    client = tweepy.Client(
        bearer_token=BEARER_TOKEN,
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_TOKEN_SECRET
    )
    user = client.get_me().data
    logging.info(f"Authenticated as: {user.username}")
    print(f"Authenticated as: {user.username}")
except tweepy.TweepyException as e:
    logging.error(f"X API v2 authentication failed: {e}")
    print(f"Authentication error: {e}")
    exit(1)

# File paths for tracking
TWEETED_POSTS_FILE = "tweeted_x_posts.json"

def load_json(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.error(f"Corrupted JSON file: {file_path}. Resetting.")
            return []
    return []

def save_json(file_path, data):
    try:
        with open(file_path, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logging.error(f"Error saving JSON to {file_path}: {e}")

def search_spacex_launch_events():
    # Target specific phrases for today's launch events
    today = datetime.now(timezone.utc).date()
    query = 'from:SpaceX ("Watch Falcon 9 launch" OR "Livestream starts" OR "Watch live" OR "Live now" OR "Liftoff of Falcon 9" OR "Falcon 9 launches" lang:en)'
    try:
        tweets = client.search_recent_tweets(query=query, max_results=10)
        if tweets.data:
            valid_tweets = []
            for tweet in tweets.data:
                if tweet.created_at:
                    created_at = datetime.fromisoformat(tweet.created_at.replace(tzinfo=timezone.utc))
                    if created_at.date() == today:
                        valid_tweets.append(tweet)
                    else:
                        logging.info(f"Skipping tweet {tweet.id} from {created_at.date()} (not today)")
                else:
                    logging.warning(f"Skipping tweet {tweet.id} with missing created_at")
            logging.info(f"Found {len(valid_tweets)} launch events for today")
            return valid_tweets
        return []
    except tweepy.TweepyException as e:
        if e.response and e.response.status_code == 429:
            logging.error(f"Rate limit exceeded for launch event search: {e}. Skipping this run.")
            return []
        logging.error(f"Error searching launch events: {e}")
        return []

def tweet_launch_event(post):
    post_id = str(post.id)
    tweeted_posts = load_json(TWEETED_POSTS_FILE)
    if post_id in tweeted_posts:
        print(f"Post {post_id} already tweeted, skipping.")
        logging.info(f"Post {post_id} already tweeted, skipping.")
        return

    text = post.text[:200] + "..." if len(post.text) > 200 else post.text
    post_url = f"https://x.com/SpaceX/status/{post_id}"
    tweet = f"SpaceX Update: {text} {post_url}"
    if len(tweet) > 280:
        text = post.text[:280 - len(post_url) - 25] + "..."
        tweet = f"SpaceX Update: {text} {post_url}"
    try:
        client.create_tweet(text=tweet)
        tweeted_posts.append(post_id)
        save_json(TWEETED_POSTS_FILE, tweeted_posts)
        print(f"Tweeted launch event: {tweet}")
        logging.info(f"Tweeted launch event: {tweet}")
    except tweepy.TweepyException as e:
        print(f"Error tweeting launch event: {e}")
        logging.error(f"Error tweeting launch event: {e}")

def search_starlink_updates():
    # Target Starlink posts twice daily
    query = 'from:Starlink (launch OR availability OR deployment lang:en)'
    try:
        tweets = client.search_recent_tweets(query=query, max_results=10)
        logging.info(f"Found {len(tweets.data or [])} Starlink posts")
        return tweets.data if tweets.data else []
    except tweepy.TweepyException as e:
        if e.response and e.response.status_code == 429:
            logging.error(f"Rate limit exceeded for Starlink search: {e}. Skipping this run.")
            return []
        logging.error(f"Error searching Starlink updates: {e}")
        return []

def tweet_starlink_update(post):
    post_id = str(post.id)
    tweeted_posts = load_json(TWEETED_POSTS_FILE)
    if post_id in tweeted_posts:
        print(f"Post {post_id} already tweeted, skipping.")
        logging.info(f"Post {post_id} already tweeted, skipping.")
        return

    text = post.text[:200] + "..." if len(post.text) > 200 else post.text
    post_url = f"https://x.com/Starlink/status/{post_id}"
    tweet = f"Starlink Update: {text} {post_url}"
    if len(tweet) > 280:
        text = post.text[:280 - len(post_url) - 25] + "..."
        tweet = f"Starlink Update: {text} {post_url}"
    try:
        client.create_tweet(text=tweet)
        tweeted_posts.append(post_id)
        save_json(TWEETED_POSTS_FILE, tweeted_posts)
        print(f"Tweeted Starlink update: {tweet}")
        logging.info(f"Tweeted Starlink update: {tweet}")
    except tweepy.TweepyException as e:
        print(f"Error tweeting Starlink update: {e}")
        logging.error(f"Error tweeting Starlink update: {e}")

def search_starship_elon():
    # Target Elon Musk's Starship posts
    query = 'from:elonmusk (Starship OR rocket OR launch OR test) -filter:retweets lang:en'
    try:
        tweets = client.search_recent_tweets(query=query, max_results=10)
        logging.info(f"Found {len(tweets.data or [])} Starship Elon posts")
        return tweets.data if tweets.data else []
    except tweepy.TweepyException as e:
        if e.response and e.response.status_code == 429:
            logging.error(f"Rate limit exceeded for Starship Elon search: {e}. Skipping this run.")
            return []
        logging.error(f"Error searching Starship Elon: {e}")
        return []

def tweet_starship_elon(post):
    post_id = str(post.id)
    tweeted_posts = load_json(TWEETED_POSTS_FILE)
    if post_id in tweeted_posts:
        print(f"Post {post_id} already tweeted, skipping.")
        logging.info(f"Post {post_id} already tweeted, skipping.")
        return

    text = post.text[:200] + "..." if len(post.text) > 200 else post.text
    post_url = f"https://x.com/elonmusk/status/{post_id}"
    tweet = f"Starship Update from Elon: {text} {post_url}"
    if len(tweet) > 280:
        text = post.text[:280 - len(post_url) - 25] + "..."
        tweet = f"Starship Update from Elon: {text} {post_url}"
    try:
        client.create_tweet(text=tweet)
        tweeted_posts.append(post_id)
        save_json(TWEETED_POSTS_FILE, tweeted_posts)
        print(f"Tweeted Starship Elon update: {tweet}")
        logging.info(f"Tweeted Starship Elon update: {tweet}")
    except tweepy.TweepyException as e:
        print(f"Error tweeting Starship Elon update: {e}")
        logging.error(f"Error tweeting Starship Elon update: {e}")

def main():
    logging.info(f"Starting script execution at {datetime.now(timezone.utc)}")
    
    # SpaceX launch events (checked every run)
    spacex_posts = search_social_updates("SpaceX", 'from:SpaceX ("Watch Falcon 9 launch" OR "Livestream starts" OR "Watch live" OR "Live now" OR "Liftoff of Falcon 9" OR "Falcon 9 launches" lang:en)')
    if spacex_posts:
        for post in spacex_posts:
            tweet_update(post, "SpaceX Update")

    # Starlink updates (twice daily at 00:00 and 12:00 UTC)
    if datetime.now(timezone.utc).hour in [0, 12]:
        starlink_posts = search_social_updates("Starlink", 'from:Starlink (launch OR availability OR deployment lang:en)')
        if starlink_posts:
            for post in starlink_posts[:2]:  # 2 writes
                tweet_update(post, "Starlink Update from Starlink")

    # Elon Musk updates (checked every run, categorized)
    elon_posts = search_social_updates("Elon", 'from:elonmusk -filter:retweets lang:en')
    if elon_posts:
        for post in elon_posts:
            category = categorize_elon_post(post.text)
            if category:
                tweet_update(post, category)

    logging.info("Script execution completed")

if __name__ == "__main__":
    main()
