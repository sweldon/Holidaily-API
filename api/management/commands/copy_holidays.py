import pymysql
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **options):
        db = pymysql.connect("mysql-db-instance.c4wxzeha18zs.us-east-1.rds.amazonaws.com", user="sweldon",
                             passwd="sweldon0704", db="whatstoday")
        cur = db.cursor()
        cur.execute("select * from holiday;")
        results = cur.fetchall()
        for h in results:
            print(h)
