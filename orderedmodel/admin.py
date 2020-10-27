from django.contrib import admin
from django.conf import settings
from django.conf.urls import patterns
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect

import urlparse
import urllib

import logging
logger = logging.getLogger('svod')
    
class OrderedModelAdmin(admin.ModelAdmin):
  ordering = ['order']
  exclude = ['order']

  def get_urls(self):
    my_urls = patterns('',
        (r'^(?P<pk>\d+)/move_up/$', self.admin_site.admin_view(self.move_up)),
        (r'^(?P<pk>\d+)/move_down/$', self.admin_site.admin_view(self.move_down)),
    )
    return my_urls + super(OrderedModelAdmin, self).get_urls()

  def reorder(self, item):
    button = '<a href="{{0}}/move_{{1}}/"><img src="{0}orderedmodel/arrow-{{1}}.gif" alt="{{1}}" /></a>'.format(settings.STATIC_URL)
    
    html = ''
    html += button.format(item.pk, 'down')
    html += '&nbsp;' + button.format(item.pk, 'up')
    return html
  reorder.allow_tags = True

  def move_down(self, request, pk):
    orderlist_queryset = self.model.objects.all()
    
    ref = request.META.get('HTTP_REFERER', '')
    if ref.find('?') != -1:
        query = urlparse.urlparse(ref).query
        query_dict = urlparse.parse_qs(query)
        
        if 'bron' in query_dict:
            bron_number = query_dict['bron'][0]
            orderlist_queryset = orderlist_queryset.filter(fk_feed_id=bron_number)

        if 'categorie' in query_dict:
            cat_number = query_dict['categorie'][0]
            orderlist_queryset = orderlist_queryset.filter(fk_category_id=cat_number)

    ordered_olqs = orderlist_queryset.order_by('order')

    if self.has_change_permission(request):
        item = get_object_or_404(self.model, pk=pk)
        try:
            next_item = ordered_olqs.filter(order__gt=item.order).order_by('order')[0]
        except IndexError: # Last item
            pass
        else:
            self.model.swap(item, next_item)

    ref = request.META.get('HTTP_REFERER', '')
    if ref.find('?') != -1:
        return HttpResponseRedirect(ref)
    else:
        return HttpResponseRedirect('../../')

  def move_up(self, request, pk):
    orderlist_queryset = self.model.objects.all()

    ref = request.META.get('HTTP_REFERER', '')
    if ref.find('?') != -1:
        query = urlparse.urlparse(ref).query
        query_dict = urlparse.parse_qs(query)
        
        if 'bron' in query_dict:
            bron_number = query_dict['bron'][0]
            orderlist_queryset = orderlist_queryset.filter(fk_feed_id=bron_number)

        if 'categorie' in query_dict:
            cat_number = query_dict['categorie'][0]
            orderlist_queryset = orderlist_queryset.filter(fk_category_id=cat_number)

    ordered_olqs = orderlist_queryset.order_by('order')

    if self.has_change_permission(request):
        item = get_object_or_404(self.model, pk=pk)

        try:
            prev_item = ordered_olqs.filter(order__lt=item.order).order_by('-order')[0]
        except IndexError: # First item
            pass
        else:
            self.model.swap(item, prev_item)

    ref = request.META.get('HTTP_REFERER', '')
    if ref.find('?') != -1:
        return HttpResponseRedirect(ref)
    else:
        return HttpResponseRedirect('../../')






