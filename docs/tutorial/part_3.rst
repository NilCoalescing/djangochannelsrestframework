Part 2: Templates
============================

We will edit the views, urls and templates for posting a Room form, and joining it.



We will edit the ``index.html`` file, for posting a new room.

.. code-block:: html

    <!-- chat/templates/chat/index.html -->
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8"/>
        <title>Chat Rooms</title>
    </head>
    <body>
        What chat room would you like to enter?<br>
        <form method="POST">
            <input id="room-name-input" name="name" type="text" size="100"><br>
            <input id="room-name-submit" type="button" value="Enter">
        </form>
    </body>
    </html>


Next, edit ``urls.py``.

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

    from django.http import HttpResponseRedirect
    from django.shortcuts import get_object_or_404, render, reverse

    from .models import Room

    def index(request):
        if request.method == "POST":
            name = request.POST.get("name", None)
            if name:
                try:
                    room = Room.manager.get(name=name)
                    return HttpResponseRedirect(reverse("room", args=[room.pk]))
                except Room.DoesNotExist:
                    pass
                room = Room.objects.create(name=name, host=request.user)
                return HttpResponseRedirect(reverse("room", args=[room.pk]))
        return render(request, 'chat/index.html')

    def room(request, pk):
        room: Room = get_object_or_404(Room, pk=pk)
        return render(request, 'chat/room.html', {
            "room":room,
        })
        




We need to create or update our `room.html` template:


.. code-block:: html

    <!-- chat/templates/chat/room.html -->
    <!DOCTYPE html>
    <html lang="us">
    <head>
        <meta charset="utf-8"/>
        <title>Chat Room</title>
    </head>
    <body>
        <textarea id="chat-log" cols="100" rows="20"></textarea><br>
        <input id="chat-message-input" type="text" size="100"><br>
        <input id="chat-message-submit" type="button" value="Send">
        <script>
            const room_pk = {{ room.pk }};
            const request_id = "{{ request.sessions.session_key }}";
            const wsURL = "ws://" + window.location.host + "/ws/chat/"
            const chatSocket = new WebSocket(wsURL);

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
            };

            chatSocket.onmessage = function (e) {
                const data = JSON.parse(e.data);
                switch (data.action) {
                    case "retrieve":
                        break;
                    case "create":
                        document.querySelector('#chat-log').value += (data.message + '\n');
                        break;
                    default:
                        break;
                }
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
                    room: room_pk,
                    action: "create_message",
                    request_id: request_id
                }));
                $('#chat-message-input').val('') ;
            });

        </script>
    </body>
    </html>

With this created w should now be able to create a room and enter it.
