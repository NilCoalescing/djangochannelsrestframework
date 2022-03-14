Tutorial Part 2: Templates
============================

We will edit the views, urls and templates for posting a Room form, and joining it.



We will edit the ``index.html`` file, for posting a new room.

.. code-block:: html

    {% extends "chat/layout.html" %}

    {% block content %}
        What chat room would you like to enter?<br>
        <form method="POST">
            <input id="room-name-input" name="name" type="text" size="100"><br>
            <input id="room-name-submit" type="button" value="Enter">
        </form>
    {% endblock content %}


.. code-block:: python

    from django.urls import path
    from . import views

    urlpatterns = [
        path('', views.index, name='index'),
        path('room/<int:pk>/', views.room, name='room'),

    ]



Editing existing views
----------------------

We will edit the ``views.py``

.. code-block:: python

    from django.shortcuts import render, reverse, get_object_or_404
    from django.views.generic import TemplateView
    from django.http import HttpResponseRedirect
    from .models import User, Room, Message

    def index(request):
        if request.method == "POST":
            name = request.POST.get("name", None)
            if name:
                room = Room.objects.create(name=name, host=request.user)
                HttpResponseRedirect(reverse("room", args=[room.pk]))  
        return render(request, 'chat/index.html')

    def room(request, pk):
        room: Room = get_object_or_404(Room, pk=pk)
        return render(request, 'chat/room.html', {
            "room":room,
        })
        

.. code-block:: html

    {% extends "chat/layout.html" %}
    {% load static %}


    {% block content %}
        <textarea id="chat-log" cols="100" rows="20"></textarea><br>
        <input id="chat-message-input" type="text" size="100"><br>
        <input id="chat-message-submit" type="button" value="Send">
    {% endblock content %}

    {% block footer %}
        <script>
            const room_pk = "{{ room.pk }}";
            const request_id = "{{ request.sessions.session_key }}";

            const chatSocket = new WebSocket(`ws://${window.location.host}/ws/chat/`);


            chatSocket.onopen = function(){
                chatSocket.send(
                    JSON.stringify({
                        pk:room_pk,
                        action:"join_room",
                        request_id:request_id,
                    })
                );
				chatSocket.send(
                    JSON.stringify({
                        pk:room_pk,
                        action:"retrieve",
                        request_id:request_id,
                    })
                );
				chatSocket.send(
                    JSON.stringify({
                        pk:room_pk,
                        action:"subscribe_to_messages_in_room",
                        request_id:request_id,
                    })
                );
				chatSocket.send(
                    JSON.stringify({
                        pk:room_pk,
                        action:"subscribe_instance",
                        request_id:request_id,
                    })
                );
            };
            
            chatSocket.onmessage = function (e) {
                const data = JSON.parse(e.data);
                switch (data.action) {
                    case "retrieve":
                        setRoom(old => data.data);
                        setMessages(old => data.messages);
                        break;
                    case "create":
                        setMessages(old => [...old, data])
                        break;
                    default:
                        break;
                }
                break;
            };

            chatSocket.onclose = function(e) {
                console.error('Chat socket closed unexpectedly');
            };

            $('#chat-message-input').focus();
            $('#chat-message-input').on('keyup', function(e){
                if (e.keyCode === 13) {  // enter, return
                    document.querySelector('#chat-message-submit').click();
                }
            });

            $('#chat-message-submit').on('click', function(e){
                const message = $('#chat-message-input').val();
                chatSocket.send(JSON.stringify({
                    message: message,
                    action: "create_message",
                    request_id: request_id
                }));
                $('#chat-message-input').val('') ;
            });

    </script>
    {% endblock footer %}
