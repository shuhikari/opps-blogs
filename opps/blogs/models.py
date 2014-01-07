#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import get_model
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ImproperlyConfigured
from django.core.exceptions import ValidationError

from mptt.models import MPTTModel, TreeForeignKey

from opps.core.models import NotUserPublishable, Slugged
from opps.articles.models import Article
from opps.images.models import Image
from opps.multimedias.models import Audio, Video

from .conf import settings


class Category(MPTTModel, NotUserPublishable):
    blog = models.ForeignKey('blogs.Blog', related_name='categories')
    name = models.CharField(_(u"Name"), max_length=140)
    slug = models.SlugField(_(u"Slug"), db_index=True, max_length=150)
    long_slug = models.SlugField(_(u"Path name"), max_length=250,
                                 db_index=True)
    show_in_menu = models.BooleanField(_(u"Show in menu?"), default=False)
    group = models.BooleanField(_(u"Group sub-channel?"), default=False)
    order = models.IntegerField(_(u"Order"), default=0)
    parent = TreeForeignKey('self', related_name='subchannel',
                            null=True, blank=True, verbose_name=_(u'Parent'))

    class Meta:
        unique_together = ("site", "long_slug", "slug", "parent")
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')
        ordering = ['name', 'parent__id', 'published']

    class MPTTMeta:
        unique_together = ("site", "blog", "long_slug")
        order_insertion_by = ['order', 'name']

    def __unicode__(self):
        """ Uniform resource identifier
        http://en.wikipedia.org/wiki/Uniform_resource_identifier
        """
        if self.parent:
            return u"/{}/{}/".format(self.parent.slug, self.slug)
        return u"/{}/".format(self.slug)

    def get_absolute_url(self):
        return u"/{}/{}{}".format(settings.OPPS_BLOGS_CHANNEL,
                                  self.blog.slug, self.__unicode__())

    @property
    def root(self):
        return self.get_root()

    def clean(self):
        category_exists = Category.objects.filter(
            slug=self.slug, site=self.site, blog=self.blog)

        if category_exists.exists() and not self.pk:
            raise ValidationError('Slug exist in domain!')

        super(Category, self).clean()

    def save(self, *args, **kwargs):
        self.long_slug = u"{}".format(self.slug)
        if self.parent:
            self.long_slug = u"{}/{}".format(self.parent.slug, self.slug)
        super(Category, self).save(*args, **kwargs)


class Blog(NotUserPublishable, Slugged):
    LAYOUT_MODES = (
        ('default', _(u'Default')),
        ('resumed', _(u'Resumed')),
    )

    user = models.ManyToManyField(settings.AUTH_USER_MODEL,
                                  verbose_name=_(u'Users'))
    name = models.CharField(_(u"Name"), max_length=140)
    main_image = models.ForeignKey(Image, verbose_name=_(u'Main Image'),
                                   blank=True, null=True)
    description = models.TextField(_(u'Description'), blank=True)
    type = models.CharField(_(u'Blog Type'), max_length=200,
                            choices=settings.OPPS_BLOGS_TYPES)
    layout_mode = models.CharField(_(u'Layout mode'), max_length=200,
                                   default='default', choices=LAYOUT_MODES)

    __unicode__ = lambda self: self.name

    def get_absolute_url(self):
        return u"/{}/{}/".format(settings.OPPS_BLOGS_CHANNEL, self.slug)

    def get_profile(self):
        if not settings.OPPS_BLOGS_PROFILE:
            raise ImproperlyConfigured(_('OPPS_BLOG_PROFILE was not found on'
                                         ' settings'))
        try:
            app_label, model_name = settings.OPPS_BLOGS_PROFILE.split('.')
        except ValueError:
            raise ImproperlyConfigured(_('OPPS_BLOGS_PROFILE must be of the'
                                         ' form "app_label.model_name"'))

        Profile = get_model(app_label, model_name)
        if Profile is None:
            raise ImproperlyConfigured("OPPS_BLOGS_PROFILE refers to model"
                                       " '%s' that has not been installed" %
                                       settings.OPPS_BLOGS_PROFILE)

        return Profile.objects.get(blog=self)

    # Template helpers  - Perhaps a templatetag should be better?
    def get_links(self):
        return self.links.filter(published=True)

    def get_categories(self):
        return self.categories.filter(published=True)

    def get_menu_categories(self):
        return self.categories.filter(published=True, show_in_menu=True)

    class Meta:
        verbose_name = _(u'Blog')
        verbose_name_plural = _(u'Blogs')
        ordering = ('name', )


class BlogPost(Article):
    blog = models.ForeignKey('blogs.Blog', verbose_name=_(u'Blog'))
    content = models.TextField(_(u"Content"))
    category = models.ForeignKey('blogs.Category', blank=True, null=True,
                                 verbose_name=_(u'Category'))
    albums = models.ManyToManyField(
        'articles.Album',
        null=True, blank=True,
        related_name='blogpoast_albums',
        verbose_name=_(u"Albums")
    )
    videos = models.ManyToManyField(Video, blank=True, null=True,
                                    through='BlogPostVideo')
    audios = models.ManyToManyField(Audio, blank=True, null=True,
                                    through='BlogPostAudio')

    accept_comments = models.BooleanField(_(u'Accept comments?'),
                                          default=True)

    class Meta:
        verbose_name = _(u'Blog post')
        verbose_name_plural = _(u'Blog Posts')

    def get_absolute_url(self):
        try:
            category = self.category
            slug = category.long_slug
        except AttributeError:
            slug = 'sem-categoria'

        return u"/{}/{}/{}/{}/".format(settings.OPPS_BLOGS_CHANNEL,
                                       self.blog.slug, slug, self.slug)


class BlogLink(NotUserPublishable):
    blog = models.ForeignKey('blogs.Blog', related_name='links')
    name = models.CharField(_(u"Name"), max_length=140)
    link = models.URLField(_('Link'))

    __unicode__ = lambda self: u"{} - {}".format(self.name, self.link)

    class Meta:
        verbose_name = _(u'Blog Link')
        verbose_name_plural = _(u'Blog Links')


class BlogPostVideo(models.Model):
    blogpost = models.ForeignKey('blogs.BlogPost', null=True, blank=True,
                                 verbose_name=_(u'Blog'),
                                 on_delete=models.SET_NULL)
    video = models.ForeignKey(Video, null=True, blank=True,
                              verbose_name=_(u'Video'),
                              on_delete=models.SET_NULL)

    class Meta:
        verbose_name = _(u'Blogpost Video')
        verbose_name_plural = _(u'Blogpost Videos')


class BlogPostAudio(models.Model):
    blogpost = models.ForeignKey('blogs.BlogPost', null=True, blank=True,
                                 verbose_name=_(u'Blog'),
                                 on_delete=models.SET_NULL)
    audio = models.ForeignKey(Audio, verbose_name=_(u'Audio'), null=True,
                              blank=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = _(u'Blogpost Audio')
        verbose_name_plural = _(u'Blogpost Audios')


@receiver(post_save, sender=Blog)
def create_blog_profile(sender, **kwargs):
    if not settings.OPPS_BLOGS_PROFILE:
        return
    if not kwargs.get('created'):
        return

    try:
        app_label, model_name = settings.OPPS_BLOGS_PROFILE.split('.')
    except ValueError:
        return

    instance = kwargs.get('instance')
    Profile = get_model(app_label, model_name)
    Profile.objects.create(blog=instance)
