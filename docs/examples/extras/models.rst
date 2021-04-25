
We will have the following ``models.py`` file, with a user model, and a comment models that is related to the user.

.. code-block:: python
    
    # models.py
    from django.db import models
    from django.contrib.auth.models import AbstractUser

    class User(AbstractUser):
        pass

    class Comment(models.Model):
        text = models.TextField()
        user = models.ForeignKey(User, related_name="comments", on_delete=models.CASCADE)
        date = models.DatetimeField(auto_now_add=True)
