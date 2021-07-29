from django.shortcuts import render, redirect
from django.http import HttpResponse
from carts.models import CartItem
from .models import Order, Payment
import datetime
import json


def payments(request):
    body = json.loads(request.body)
    order = Order.objects.get(user=request.user, is_ordered=False, order_number=body['orderID'])
    print(body)
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
    return render(request, 'orders/payments.html')


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

