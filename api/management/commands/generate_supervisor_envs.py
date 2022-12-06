
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--profile")

    def handle(self, *args, **options):
    
        profile = options.get("profile")
        if not profile:
            print("Please provide a file with exported envvars")
            return

        with open(profile, "r") as profile_file:

           lines = profile_file.read().splitlines() 
           env_str = ""
           for l in lines:
               if "export" not in l.lower():
                   continue
               l = l.replace("export ", "")
               env_str += l+","

        env_str = env_str.rstrip(",")
        print("[supervisord]\nenvironment={}".format(env_str))
