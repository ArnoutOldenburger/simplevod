from django.db import connection, models
from django.contrib.auth.models import User
from orderedmodel import OrderedModel
from datetime import datetime  

import logging
logger = logging.getLogger('svod')

SIMPLEVOD_NEW_CATEGORY      = 'Nieuw'
IDAT_RECENT_CATEGORY        = '#recent-category'
IDAT_DEFAULT_CATEGORY       = '#category-999'

SIMPLEVOD_SOURCE_FTP        = 0
SIMPLEVOD_SOURCE_JSON       = 1
SIMPLEVOD_SOURCE_XML        = 2
SIMPLEVOD_SOURCE_FILE       = 3

SIMPLEVOD_SOURCE_NAME_FTP   = 'FTP'
SIMPLEVOD_SOURCE_NAME_JSON  = 'JSON'
SIMPLEVOD_SOURCE_NAME_XML   = 'XML'
SIMPLEVOD_SOURCE_NAME_FILE  = 'FILE'

class AuthUser(models.Model):
    username = models.CharField(unique=True, max_length=30)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.CharField(max_length=75)
    password = models.CharField(max_length=128)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField()
    is_superuser = models.BooleanField(default=True)
    last_login = models.DateTimeField()
    date_joined = models.DateTimeField()

    def __unicode__(self):
        return u'%s' % (self.username)

    class Meta:
        ordering = ['username',]
        db_table = u'auth_user'
        verbose_name_plural = "    Users - Onderhoud Gebruiker Accounts "

class DjangoContentType(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=100)
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    class Meta:
        db_table = 'django_content_type'

class AuthPermission(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=50)
    content_type = models.ForeignKey('DjangoContentType')
    codename = models.CharField(max_length=100)

    class Meta:
        db_table = 'auth_permission'

class AuthUserUserPermissions(models.Model):
    id = models.IntegerField(primary_key=True)
    user = models.ForeignKey(AuthUser)
    permission = models.ForeignKey(AuthPermission)
    class Meta:
        db_table = 'auth_user_user_permissions'
    	
class SimplevodUser(models.Model):
    administrator = models.CharField(max_length=50, blank=True)
    fk_feed = models.ForeignKey('Feed', null=True, blank=True, on_delete=models.SET_NULL)
    is_superuser = models.BooleanField(editable=False)    
    description = models.CharField(max_length=50, null=True)

    def __unicode__(self):
        return u'%d' % (self.id)

    class Meta:
        verbose_name_plural = "     beheerder - simplevod beheerder gekoppeld aan bron"
        unique_together = ('administrator', 'fk_feed')
        
class Category(OrderedModel):
    oldorder = models.BigIntegerField(null=True, unique=False)
    idat = models.TextField()
    title = models.TextField()
    fk_feed = models.ForeignKey('Feed')
    active = models.BooleanField(default=True)    
    is_new = models.BooleanField(default=False)    

    def __init__(self, *args, **kwargs):
        super(Category, self).__init__(*args, **kwargs)
        self.oldorder = kwargs.get('oldorder', 0)
                
    def __unicode__(self):
        return u'%s' % (self.title)
        
    class Meta:
        verbose_name_plural = "  categorie - categorie van video-on-demand per bron"
        unique_together = ('title', 'fk_feed')

class Tvod(OrderedModel):
    oldorder = models.BigIntegerField(null=True, unique=False)
    idat = models.TextField()
    videoref = models.TextField()
    title = models.TextField()
    productcode = models.TextField()
    enduseramount = models.SmallIntegerField(default=0)
    amount = models.SmallIntegerField(default=0)
    skipconfirm = models.SmallIntegerField(default=1)
    expiry_period = models.CharField(max_length=6, default="172800")
    status = models.TextField()
    productdescription = models.TextField()
    fk_feed = models.ForeignKey('Feed')
    fk_category = models.ForeignKey('Category', null=True)
    active = models.BooleanField(default=True)    
    is_new = models.BooleanField(default=False)    
        
    def __unicode__(self):
        return u'%s' % (self.title)
        
    class Meta:
        verbose_name_plural = "   video     - details video-on-demand"

class New(models.Model):
    idat = models.TextField()
    videoref = models.TextField()
    title = models.TextField()
    productcode = models.TextField()
    enduseramount = models.SmallIntegerField(default=0)
    amount = models.SmallIntegerField(default=0)
    skipconfirm = models.SmallIntegerField(default=1)
    expiry_period = models.CharField(max_length=6, default="172800")
    status = models.TextField()
    productdescription = models.TextField()
    fk_feed = models.ForeignKey('Feed')
    fk_category = models.ForeignKey('Category', null=True)
    active = models.BooleanField(default=False)    
    is_new = models.BooleanField(default=True)    
    is_django = models.BooleanField(default=True)    

class Feed(models.Model):
    name = models.TextField()
    url = models.TextField()
    xml = models.TextField()
    #retrieve = models.SmallIntegerField(default=0, choices= ((0, u'FTP',), (1, u'JSON'), (2, u'XML')))
    retrieve = models.SmallIntegerField(default=1, choices= ((SIMPLEVOD_SOURCE_JSON, SIMPLEVOD_SOURCE_NAME_JSON), (SIMPLEVOD_SOURCE_XML, SIMPLEVOD_SOURCE_NAME_XML), (SIMPLEVOD_SOURCE_FILE, SIMPLEVOD_SOURCE_NAME_FILE)))
    style = models.TextField()
    title = models.TextField()
    etag = models.TextField()
    is_django = models.BooleanField(default=True)    
    use_category = models.BooleanField(default=True)    

    def __unicode__(self):
        return u'%s' % (self.title)
     
    def aantal_videos(self):
        aantal_videos = Tvod.objects.filter(fk_feed=self).count()
        return aantal_videos     
        
    class Meta:
        verbose_name_plural = "    bron    - bronnen van video-on-demand bestanden"


