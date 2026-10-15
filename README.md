# Campus Marketplace

A website where international students at Sichuan University can sell, buy or give away second-hand items.

Built with Python and Django.

## Features

- Sign up, log in and log out
- Public profile pages and profile editing
- Sell an item with up to 5 photos (5 MB each)
- Edit, delete and mark your items as sold (only the owner can do this)
- "My listings" page
- Search, category and campus filters, and pages of 12 items
- Messaging between a buyer and a seller, with an inbox and an unread-message badge

## How to run it

You need Python 3.12 or newer.

1. Create and activate a virtual environment:

   ```
   python -m venv venv
   venv\Scripts\activate
   ```

2. Install the packages:

   ```
   pip install -r requirements.txt
   ```

3. Create your settings file. Copy `.env.example` to `.env`, then open `.env` and replace the `SECRET_KEY` value with a long random text. You can make one with:

   ```
   python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
   ```

4. Create the database:

   ```
   python manage.py migrate
   ```

5. Create an admin account, then start the site:

   ```
   python manage.py createsuperuser
   python manage.py runserver
   ```

6. Open http://127.0.0.1:8000/ in your browser. Log in to the admin page at http://127.0.0.1:8000/admin/ and add a few categories (for example Books, Furniture, Electronics) before you create your first listing.

## Settings (.env)

| Name | Meaning |
| --- | --- |
| `SECRET_KEY` | Secret text Django uses for security. Keep it private. |
| `DEBUG` | `True` while building. Must be `False` on a real website. |
| `ALLOWED_HOSTS` | Website addresses allowed to use the site, separated by commas. Needed when `DEBUG` is `False`. |

The `.env` file is never committed to git.

## Project layout

- `accounts/` - sign up, log in, profiles
- `listings/` - items for sale, photos, search and filters
- `messaging/` - conversations and messages
- `templates/` - HTML pages
- `static/` - CSS

## Run the tests

```
python manage.py test
```
