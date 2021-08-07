from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, ReviewRating
from category.models import Category
from carts.models import Cart, CartItem
from carts.views import _cart_id
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .forms import ReviewForm

# Create your views here.


def store(request, category_slug=None):
    categories = None
    products = None
    if category_slug is not None:
        categories = get_object_or_404(Category, slug=category_slug)
        products = Product.objects.filter(category=categories, is_available=True).order_by('-id')
        products_count = products.count()
    else:
        products = Product.objects.all().filter(is_available=True).order_by('-id')
        products_count = products.count()
    paginator = Paginator(products, 6)
    page = request.GET.get('page')
    paginated_products = paginator.get_page(page)

    context = {
        'products': paginated_products,
        'products_count': products_count,

    }
    return render(request, 'store/store.html', context)


def product_detail(request, category_slug, product_slug):
    try:
        single_object = Product.objects.get(category__slug=category_slug, slug=product_slug)
        in_cart = CartItem.objects.filter(cart__cart_id=_cart_id(request), product=single_object).exists()
    except Exception as e:
        raise e

    reviews = ReviewRating.objects.filter(product_id=single_object.id, status=True)

    context = {
        'product': single_object,
        'in_cart': in_cart,
        'reviews': reviews,
    }
    return render(request, 'store/product-detail.html', context=context)


def search(request):
    products = None
    products_count = 0
    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        if keyword:
            products = Product.objects.order_by('-created_date').filter(Q(product_name__icontains=keyword)
                                                                        | Q(description__icontains=keyword))
            products_count = products.count()
    context = {
        'products': products,
        'products_count': products_count,
    }
    return render(request, 'store/store.html', context)


def submit_review(request, product_id):
    url = request.META.get('HTTP_REFERER')
    if request.method == 'POST':
        try:
            reviews = ReviewRating.objects.get(user__id=request.user.id, product__id=product_id)
            form = ReviewForm(request.POST, instance=reviews)
            form.save()
            messages.success(request, 'Thank you! Your review has been updated.')
            return redirect(url)
        except ReviewRating.DoesNotExist:
            form = ReviewForm(request.POST)
            if form.is_valid():
                data = ReviewRating()
                data.subject = form.cleaned_data['subject']
                data.rating = form.cleaned_data['rating']
                data.review = form.cleaned_data['review']
                data.ip = request.META.get('REMOTE_ADDR')
                data.product_id = product_id
                data.user_id = request.user.id
                data.save()
                messages.success(request, 'Thank you! Your review has been submitted.')
                return redirect(url)
