# Holidaily-API
A DRF based API for Holidaily and DVNT applications

## Set up
1. Ensure you're running on python 3.9. A virtual environment is recommended.
2. Clone repository
3. In root of repo, run `pip install -r requirements.txt`
4. After that, in the same directory run `pre-commit install`. Black and Flake8 ensure good formatting before all commits.

## Production with Apache
1. Install system-level apache2-dev for ubuntu after installing apache2	
2. `pip uninstall mod_wsgi` if necessary
3. `sudo apt-get remove libapache2-mod-wsgi-py3` if necessary
4. `pip install mod_wsgi`
5. `mod_wsgi-express module-config`
6. Paste the result from step 5 in `/etc/mods-available/wsgi.load`
7. `sudo a2enmod wsgi`
8. Add this GIST to `/etc/apache2/sites-available/000-default.conf`: https://gist.github.com/sweldon/ee9e4fb88efce238623bfd58d6eed92d
	- Be sure to update the virtual env path on line 1
	- Update 'yourdomain.com' to what you will be linking to Certbot (keep reading to set up certbot after this)
9. `sudo a2ensite 000-default.conf`
10. Ensure envvars are in `/etc/apache2/envvars`
11. Set up certbot, it will update your config from step 8: https://certbot.eff.org/instructions?ws=apache&os=ubuntufocal
	- This assumes youve setup the domain name via route53 and godaddy
12. Setup celery
	- Copy this gist to `/etc/supervisor/conf.d/celery.conf`: https://gist.github.com/sweldon/2268a63439e5209587e26d6f148ffc75
	- Check out comments of gist for instructions and notes
	- **Don't forget to update the envvars in that gist**
	- You can use the `generate_supervisor_envs` management command to help get it in a format you can paste in
	- Check with `sudo ps auxww | grep "holidaily worker" | grep -v "grep" | awk '{print $2}'`
	- Restart with `sudo ps auxww | grep "holidaily worker" | grep -v "grep" | awk '{print $2}' | sudo xargs kill -HUP`
