from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    url(r'^simplevod/$', 'simplevod.views.index'),
    url(r'^browse/(?P<feed_name>\w+)/$', 'simplevod.views.browse', name='browse'),
    url(r'^category/(?P<style>\w+)/(?P<is_new>\w+)/(?P<feed_id>\w+)/(?P<category_id>\S+)/$', 'simplevod.views.category', name='category'),
    url(r'^play/(?P<style>\w+)/(?P<is_new>\w+)/(?P<feed_id>\w+)/(?P<category_id>\S+)/(?P<item_id>\S+)/$', 'simplevod.views.play', name='play'),
    url(r'^tvod/(?P<feed_id>\w+)/(?P<category_id>\S+)/(?P<item_id>\S+)/$', 'simplevod.views.tvod', name='tvod'),
    url(r'^ajax_tvod_combobox/$', 'simplevod.views.ajax_tvod_combobox', name='ajax_tvod_combobox'),
    url(r'^ajax_category_combobox/$', 'simplevod.views.ajax_category_combobox', name='ajax_category_combobox'),
)

