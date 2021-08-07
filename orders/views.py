from django.shortcuts import render, redirect
from django.http import JsonResponse
from carts.models import CartItem
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from .models import Order, Payment, OrderProduct
from carts.models import Product
import datetime
import json


def payments(request):
    body = json.loads(request.body)
    order = Order.objects.get(user=request.user, is_ordered=False, order_number=body['orderID'])
    payment = Payment(
        user=request.user,
        payment_id=body['transID'],
        payment_method=body['payment_method'],
        amount_paid=order.order_total,
        status=body['status'],
    )
    payment.save()
    order.payment = payment
    order.is_ordered = True
    order.save()

    # Move the Cart Items to Order Table

    cart_items = CartItem.objects.filter(user=request.user)
    for item in cart_items:
        order_product = OrderProduct()
        order_product.order_id = order.id
        order_product.payment = payment
        order_product.user_id = request.user.id
        order_product.product_id = item.product_id
        order_product.quantity = item.quantity
        order_product.product_price = item.product.price
        order_product.ordered = True
        order_product.save()

        cart_item = CartItem.objects.get(id=item.id)
        product_variation = cart_item.variations.all()
        order_product.variations.set(product_variation)
        order_product.save()

    # Reduce quantity of sold products

        product = Product.objects.get(id=item.product_id)
        product.stock -= item.quantity
        product.save()

    # Clear cart
    
    CartItem.objects.filter(user=request.user).delete()

    # Send order received to user mail

    mail_subject = 'Thank you for your order!'
    message = render_to_string('orders/order_received_email.html', {
        'user': request.user,
        'order': order,
    })
    to_email = request.user.email
    send_email = EmailMessage(mail_subject, message, to=[to_email])
    send_email.send()

    # Send order number and transaction id back to send data

    data = {
        'order_number': order.order_number,
        'transID': payment.payment_id,
    }
    return JsonResponse(data)


def place_order(request, total=0, quantity=0):
    current_user = request.user
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store')

    grand_total = 0
    tax = 0
    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity
    tax = (2 * total) / 100
    grand_total = total + tax

    if request.method == 'POST':
        user = current_user
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        phone = request.POST['phone_number']
        email = request.POST['email']
        address_line_1 = request.POST['address_line_1']
        address_line_2 = request.POST['address_line_2']
        country = request.POST['country']
        state = request.POST['state']
        city = request.POST['city']
        order_note = request.POST['order_note']
        order_total = grand_total
        tax = tax
        # Generate order number
        ip = request.META.get('REMOTE_ADDR')
        order = Order.objects.create(user=user,
                                     first_name=first_name,
                                     last_name=last_name,
                                     phone=phone,
                                     email=email,
                                     address_line_1=address_line_1,
                                     address_line_2=address_line_2,
                                     country=country,
                                     state=state,
                                     city=city,
                                     order_note=order_note,
                                     order_total=order_total,
                                     tax=tax,
                                     ip=ip)
        order.save()
        yr = int(datetime.date.today().strftime('%Y'))
        dt = int(datetime.date.today().strftime('%d'))
        mt = int(datetime.date.today().strftime('%m'))
        d = datetime.date(yr, mt, dt)
        current_date = d.strftime('%Y%m%d')
        order_number = current_date + str(order.id)
        order.order_number = order_number
        order.save()

        current_order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)
        context = {
            'order': current_order,
            'cart_items': cart_items,
            'total': total,
            'tax': tax,
            'grand_total': grand_total
        }
        return render(request, 'orders/payments.html', context)
    else:
        return redirect('checkout')


def order_complete(request):
    order_number = request.GET.get('order_number')
    transID = request.GET.get('payment_id')
    try:
        order = Order.objects.get(order_number=order_number, is_ordered=True)
        ordered_products = OrderProduct.objects.filter(order_id=order.id)
        subtotal = 0
        for i in ordered_products:
            subtotal += i.product_price * i.quantity
        context = {
            'order': order,
            'ordered_products': ordered_products,
            'transID': transID,
            'subtotal': subtotal,
        }
        return render(request, 'orders/order_complete.html', context)
    except (Payment.DoesNotExist, Order.DoesNotExist):
        return redirect('home')
