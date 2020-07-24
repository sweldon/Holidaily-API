from django.core.management.base import BaseCommand
from django.utils import timezone
from elasticsearch.client import IndicesClient
from elasticsearch_dsl import Search

from api.models import Holiday
from holidaily.settings import ES_CLIENT, TWEET_INDEX_NAME, TWITTER_CLIENT
from itertools import chain, zip_longest


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--recreate_index")
        parser.add_argument(
            "--images_only", dest="feature", default=False, action="store_true"
        )
        parser.add_argument("--tweet_type")

    @staticmethod
    def _create_index(index_name):
        indices_client = IndicesClient(client=ES_CLIENT)
        if indices_client.exists(index_name):
            indices_client.delete(index=index_name)
        indices_client.create(index=index_name)
        print(f"Recreated index: {index_name}")

    @staticmethod
    def _clean_tweet(tweet_data):
        tweet = {}
        tweet["user"] = tweet_data.get("user", {}).get("name")
        tweet["body"] = tweet_data.get("full_text")
        tweet["timestamp"] = tweet_data.get("created_at")
        tweet["twitter_id"] = tweet_data.get("id")
        tweet["user_profile_image"] = tweet_data.get("user", {}).get(
            "profile_image_url_https"
        )

        tweet_media = tweet_data.get("entities", {}).get("media", {})
        if len(tweet_media) > 0:
            tweet["image"] = tweet_media[0].get("media_url_https")
        else:
            quoted_media = (
                tweet_data.get("quoted_status", {}).get("entities", {}).get("media", {})
            )
            if len(quoted_media) > 0:
                tweet["image"] = quoted_media[0].get("media_url_https")
                print(f"Found media in a quoted tweet {quoted_media[0].get('id')}")

        return tweet

    @staticmethod
    def tweet_exists(tweet):
        tweet_id = tweet.get("twitter_id")
        kwargs = {
            "index": "tweets",
            "doc_type": "tweet",
            "id": tweet_id,
        }
        return True if ES_CLIENT.exists(**kwargs) else False

    @staticmethod
    def delete_tweet(tweet):
        tweet_id = tweet.get("twitter_id")
        kwargs = {
            "index": "tweets",
            "doc_type": "tweet",
            "id": tweet_id,
        }

        if ES_CLIENT.exists(**kwargs):
            ES_CLIENT.delete(**kwargs)
            print(f"Deleted tweet {tweet_id} from ES")
        else:
            print(f"Tweet with id {tweet_id} does not exist in ES")

    @staticmethod
    def _interleave(l1, l2):
        return [x for x in chain(*zip_longest(l1, l2)) if x is not None]

    def handle(self, *args, **options):
        recreate = options.get("recreate_index")
        images_only = options.get("images_only")
        tweet_type = options.get("tweet_type")

        today = timezone.now().date()
        todays_holidays = Holiday.objects.filter(date=today, active=True)

        hashtags = [f"#{h.name.replace(' ','')}" for h in todays_holidays]

        if recreate:
            self._create_index(index_name="tweets")

        last_indexed_tweet = None
        if not recreate:
            last_indexed_tweet = (
                (Search(using=ES_CLIENT, index=TWEET_INDEX_NAME).sort("-twitter_id"))
                .source(["twitter_id", "timestamp"])[:1]
                .execute()
                .hits[0]
                .to_dict()
            )

            print(
                f"Indexing tweets since {last_indexed_tweet.get('timestamp')} "
                f"(id {last_indexed_tweet.get('twitter_id')})"
            )

        results = []
        images_only = "filter:images" if images_only else ""
        for trend in hashtags:
            search_str_filtered = f"{trend} filter:safe -filter:retweets {images_only}"
            trend_results = TWITTER_CLIENT.GetSearch(
                term=search_str_filtered,
                result_type=tweet_type if tweet_type else "mixed",
                return_json=True,
                count=30,
                since_id=last_indexed_tweet.get("twitter_id") if not recreate else None,
            )["statuses"]

            for r in trend_results:
                results.append(r)

        for tweet in results:
            tweet = self._clean_tweet(tweet)
            # since_id should be new tweets, but check existence just in case
            if not self.tweet_exists(tweet):
                ES_CLIENT.index(
                    index="tweets",
                    doc_type="tweet",
                    body=tweet,
                    id=tweet.get("twitter_id"),
                )
                print(f"Indexed tweet {tweet.get('twitter_id')}")
