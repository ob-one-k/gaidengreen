SlateportCity_House_MapScripts::
	.byte 0

SlateportCity_House_EventScript_PokefanM::
	msgbox SlateportCity_House_Text_NatureToDoWithStatGains, MSGBOX_NPC
	end

SlateportCity_House_EventScript_Girl::
	msgbox SlateportCity_House_Text_MustBeGoingToBattleTent, MSGBOX_NPC
	end

SlateportCity_House_EventScript_EggNpc::
	lock
	faceplayer
	goto_if_set FLAG_RECEIVED_EEVEE_EGG, SlateportCity_House_EventScript_EggNpc_AlreadyGot

	msgbox SlateportCity_House_Text_EggOffer, MSGBOX_DEFAULT
	giveegg SPECIES_EEVEE
	setflag FLAG_RECEIVED_EEVEE_EGG
	msgbox SlateportCity_House_Text_EggGiven, MSGBOX_DEFAULT
	release
	end

SlateportCity_House_EventScript_EggNpc_AlreadyGot:
	msgbox SlateportCity_House_Text_EggNpc_AlreadyGot, MSGBOX_DEFAULT
	release
	end

SlateportCity_House_Text_EggOffer:
	.string "I have a POKéMON EGG for you.$"

SlateportCity_House_Text_EggGiven:
	.string "Please take good care of it.$"

SlateportCity_House_Text_EggNpc_AlreadyGot:
	.string "How is that EGG doing?$"

SlateportCity_House_Text_NatureToDoWithStatGains:
	.string "My POKéMON has a HASTY nature.\p"
	.string "It has higher SPEED compared to\n"
	.string "my other POKéMON.\p"
	.string "Maybe their nature has something to\n"
	.string "do with the stat gains of POKéMON.$"

SlateportCity_House_Text_MustBeGoingToBattleTent:
	.string "You're a TRAINER, aren't you?\p"
	.string "Since you came to SLATEPORT CITY,\n"
	.string "you must be going to the BATTLE TENT.$"

