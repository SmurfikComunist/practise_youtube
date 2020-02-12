# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class FavoriteVideo(models.Model):
    id_favorite_video = models.AutoField(primary_key=True)
    id_video = models.CharField(unique=True, max_length=255)

    class Meta:
        managed = False
        db_table = 'favorite_video'


class Page(models.Model):
    id_page = models.AutoField(primary_key=True)
    page_token = models.CharField(unique=True, max_length=255)

    class Meta:
        managed = False
        db_table = 'page'


class SavedSearchQuery(models.Model):
    id_saved_search_query = models.AutoField(primary_key=True)
    query = models.CharField(unique=True, max_length=255)

    class Meta:
        managed = False
        db_table = 'saved_search_query'


class SavedSearchResult(models.Model):
    id_saved_search_result = models.AutoField(primary_key=True)
    id_saved_search_query = models.ForeignKey(SavedSearchQuery, models.DO_NOTHING, db_column='id_saved_search_query')
    id_saved_search_video = models.ForeignKey('SavedSearchVideo', models.DO_NOTHING, db_column='id_saved_search_video')
    id_page = models.ForeignKey(Page, models.DO_NOTHING, db_column='id_page', blank=True, null=True,
                                related_name="related_id_page")
    id_next_page = models.ForeignKey(Page, models.DO_NOTHING, db_column='id_next_page',
                                     related_name="related_id_next_page")

    class Meta:
        managed = False
        db_table = 'saved_search_result'


class SavedSearchVideo(models.Model):
    id_saved_search_video = models.AutoField(primary_key=True)
    id_video = models.CharField(unique=True, max_length=255)
    title = models.CharField(max_length=255)
    published_at = models.DateTimeField(blank=True, null=True)
    thumbnail_url = models.CharField(max_length=500)

    class Meta:
        managed = False
        db_table = 'saved_search_video'
