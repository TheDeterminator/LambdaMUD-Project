# API used for all player commands/actions in the game
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from pusher import Pusher
from django.http import JsonResponse
from decouple import config
from django.contrib.auth.models import User
from .models import *
from rest_framework.decorators import api_view
import json

# instantiate pusher
pusher = Pusher(app_id=config('PUSHER_APP_ID'), key=config('PUSHER_KEY'), secret=config('PUSHER_SECRET'), cluster=config('PUSHER_CLUSTER'))

"""Puts the player into the game inside of whatever room they were in when they were last in the game
takes a request as argment and returns a json value with player name, uuid and room location"""
@csrf_exempt
@api_view(["GET"])
def initialize(request):
    user = request.user
    player = user.player
    player_id = player.id
    uuid = player.uuid
    room = player.room()
    players = room.playerNames(player_id)
    return JsonResponse({'uuid': uuid, 'name':player.user.username, 'title':room.title, 'description':room.description, 'players':players}, safe=True)

"""Moves the player from one room to another and broadcasts player's movement throughout rooms
takes in a request object and returns a json response with player and room info"""
# @csrf_exempt
@api_view(["POST"])
def move(request):
    dirs={"n": "north", "s": "south", "e": "east", "w": "west"}
    reverse_dirs = {"n": "south", "s": "north", "e": "west", "w": "east"}
    player = request.user.player
    player_id = player.id
    player_uuid = player.uuid
    data = json.loads(request.body)
    direction = data['direction']
    room = player.room()
    nextRoomID = None
    if direction == "n":
        nextRoomID = room.n_to
    elif direction == "s":
        nextRoomID = room.s_to
    elif direction == "e":
        nextRoomID = room.e_to
    elif direction == "w":
        nextRoomID = room.w_to
    if nextRoomID is not None and nextRoomID > 0:
        nextRoom = Room.objects.get(id=nextRoomID)
        player.currentRoom=nextRoomID
        player.save()
        players = nextRoom.playerNames(player_id)
        currentPlayerUUIDs = room.playerUUIDs(player_id)
        nextPlayerUUIDs = nextRoom.playerUUIDs(player_id)
        for p_uuid in currentPlayerUUIDs:
            pusher.trigger(f'p-channel-{p_uuid}', u'broadcast', {'message':f'{player.user.username} has walked {dirs[direction]}.'})
        for p_uuid in nextPlayerUUIDs:
            pusher.trigger(f'p-channel-{p_uuid}', u'broadcast', {'message':f'{player.user.username} has entered from the {reverse_dirs[direction]}.'})
        return JsonResponse({'name':player.user.username, 'title':nextRoom.title, 'description':nextRoom.description, 'players':players, 'error_msg':""}, safe=True)
    else:
        players = room.playerNames(player_uuid)
        return JsonResponse({'name':player.user.username, 'title':room.title, 'description':room.description, 'players':players, 'error_msg':"You cannot move that way."}, safe=True)


"""Allows a player to broadcast a message to other players in the room
receives a request object containing message info and returns a JSON response with the message info"""
@csrf_exempt
@api_view(["POST"])
def say(request):
    player = request.user.player
    player_id = player.id
    player_uuid = player.uuid
    data = json.loads(request.body)
    message = data['message']
    room = player.room()
    playerUUIDs = room.playerUUIDs(player_id)
    if message:
	    for p_uuid in playerUUIDs:
	        pusher.trigger(f'p-channel-{p_uuid}', u'broadcast', {'message':f'{message}'})
	    return JsonResponse({'name':player.user.username, 'message':message, 'error_msg':""}, safe=True)
    else:
	    return JsonResponse({'error':"Something is wrong"}, safe=True, status=500)

"""Allows a player to broadcast a message to all players in game
receives a request object containing message info and returns a JSON response with the message info"""
@csrf_exempt
@api_view(["POST"])
def shout(request):
    player = request.user.player
    player_id = player.id
    player_uuid = player.uuid
    data = json.loads(request.body)
    message = data['message']
    players = Player.objects.all()
    if message:
	    for playerMod in players:
	        pusher.trigger(f'p-channel-{playerMod.uuid}', u'broadcast', {'message':f'{message}'})
	    return JsonResponse({'name':player.user.username, 'message':message, 'error_msg':""}, safe=True)
    else:
	    return JsonResponse({'error':"Something is wrong"}, safe=True, status=500)

