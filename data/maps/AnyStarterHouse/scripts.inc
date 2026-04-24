AnyStarterHouse_MapScripts::
	.byte 0


SafariZone_EventScript_StarterAdvertiser::
	lock
	faceplayer
	goto_if_set FLAG_RECEIVED_SAFARI_STARTER, SafariZone_EventScript_AlreadyPicked

	msgbox SafariZone_Text_Intro, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, SafariZone_EventScript_NoThanks
	goto SafariZone_EventScript_TypeMenuPage1

SafariZone_EventScript_TypeMenuPage1::
	message SafariZone_Text_ChooseType
	waitmessage
	multichoice 0, 0, MULTI_SAFARI_TYPES_PAGE_1, FALSE
	switch VAR_RESULT
	case 0, SafariZone_EventScript_PickGrass
	case 1, SafariZone_EventScript_PickFire
	case 2, SafariZone_EventScript_PickWater
	case 3, SafariZone_EventScript_PickNormal
	case 4, SafariZone_EventScript_PickFighting
	case 5, SafariZone_EventScript_PickGhost
	case 6, SafariZone_EventScript_GoToPage2
	case MULTI_B_PRESSED, SafariZone_EventScript_Cancel
	end

SafariZone_EventScript_GoToPage2::
	message SafariZone_Text_ChooseType
	waitmessage
	multichoice 0, 0, MULTI_SAFARI_TYPES_PAGE_2, FALSE
	switch VAR_RESULT
	case 0, SafariZone_EventScript_PickDark
	case 1, SafariZone_EventScript_PickPsychic
	case 2, SafariZone_EventScript_PickFairy
	case 3, SafariZone_EventScript_PickDragon
	case 4, SafariZone_EventScript_PickSteel
	case 5, SafariZone_EventScript_PickBug
	case 6, SafariZone_EventScript_GoToPage3
	case MULTI_B_PRESSED, SafariZone_EventScript_Cancel
	end

SafariZone_EventScript_GoToPage3::
	message SafariZone_Text_ChooseType
	waitmessage
	multichoice 0, 0, MULTI_SAFARI_TYPES_PAGE_3, FALSE
	switch VAR_RESULT
	case 0, SafariZone_EventScript_PickGround
	case 1, SafariZone_EventScript_PickRock
	case 2, SafariZone_EventScript_PickIce
	case 3, SafariZone_EventScript_PickPoison
	case 4, SafariZone_EventScript_PickElectric
	case 5, SafariZone_EventScript_PickFlying
	case 6, SafariZone_EventScript_TypeMenuPage1
	case MULTI_B_PRESSED, SafariZone_EventScript_Cancel
	end

SafariZone_EventScript_Cancel::
	msgbox SafariZone_Text_NoThanks, MSGBOX_DEFAULT
	release
	end

SafariZone_EventScript_NoThanks::
	msgbox SafariZone_Text_NoThanks, MSGBOX_DEFAULT
	release
	end

SafariZone_EventScript_AlreadyPicked::
	msgbox SafariZone_Text_AlreadyPicked, MSGBOX_DEFAULT
	release
	end

SafariZone_EventScript_PickBug::
	setvar VAR_0x8004, SPECIES_SEWADDLE
	msgbox SafariZone_Text_ConfirmBug, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, SafariZone_EventScript_TypeMenuPage1
	goto SafariZone_EventScript_GiveChosenStarter

SafariZone_EventScript_PickDark::
	setvar VAR_0x8004, SPECIES_PAWNIARD
	msgbox SafariZone_Text_ConfirmDark, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, SafariZone_EventScript_TypeMenuPage1
	goto SafariZone_EventScript_GiveChosenStarter

SafariZone_EventScript_PickDragon::
	setvar VAR_0x8004, SPECIES_AXEW
	msgbox SafariZone_Text_ConfirmDragon, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, SafariZone_EventScript_TypeMenuPage1
	goto SafariZone_EventScript_GiveChosenStarter

SafariZone_EventScript_PickElectric::
	setvar VAR_0x8004, SPECIES_ELEKID
	msgbox SafariZone_Text_ConfirmElectric, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, SafariZone_EventScript_TypeMenuPage1
	goto SafariZone_EventScript_GiveChosenStarter

SafariZone_EventScript_PickFairy::
	setvar VAR_0x8004, SPECIES_TOGEPI
	msgbox SafariZone_Text_ConfirmFairy, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, SafariZone_EventScript_TypeMenuPage1
	goto SafariZone_EventScript_GiveChosenStarter

SafariZone_EventScript_PickFighting::
	setvar VAR_0x8004, SPECIES_MACHOP
	msgbox SafariZone_Text_ConfirmFighting, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, SafariZone_EventScript_TypeMenuPage1
	goto SafariZone_EventScript_GiveChosenStarter

SafariZone_EventScript_PickFire::
	setvar VAR_0x8004, SPECIES_FENNEKIN
	msgbox SafariZone_Text_ConfirmFire, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, SafariZone_EventScript_TypeMenuPage1
	goto SafariZone_EventScript_GiveChosenStarter

SafariZone_EventScript_PickFlying::
	setvar VAR_0x8004, SPECIES_ROOKIDEE
	msgbox SafariZone_Text_ConfirmFlying, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, SafariZone_EventScript_TypeMenuPage1
	goto SafariZone_EventScript_GiveChosenStarter

SafariZone_EventScript_PickGhost::
	setvar VAR_0x8004, SPECIES_GASTLY
	msgbox SafariZone_Text_ConfirmGhost, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, SafariZone_EventScript_TypeMenuPage1
	goto SafariZone_EventScript_GiveChosenStarter

SafariZone_EventScript_PickGrass::
	setvar VAR_0x8004, SPECIES_TURTWIG
	msgbox SafariZone_Text_ConfirmGrass, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, SafariZone_EventScript_TypeMenuPage1
	goto SafariZone_EventScript_GiveChosenStarter

SafariZone_EventScript_PickGround::
	setvar VAR_0x8004, SPECIES_GLIGAR
	msgbox SafariZone_Text_ConfirmGround, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, SafariZone_EventScript_TypeMenuPage1
	goto SafariZone_EventScript_GiveChosenStarter

SafariZone_EventScript_PickIce::
	setvar VAR_0x8004, SPECIES_SPHEAL
	msgbox SafariZone_Text_ConfirmIce, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, SafariZone_EventScript_TypeMenuPage1
	goto SafariZone_EventScript_GiveChosenStarter

SafariZone_EventScript_PickNormal::
	setvar VAR_0x8004, SPECIES_MUNCHLAX
	msgbox SafariZone_Text_ConfirmNormal, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, SafariZone_EventScript_TypeMenuPage1
	goto SafariZone_EventScript_GiveChosenStarter

SafariZone_EventScript_PickPoison::
	setvar VAR_0x8004, SPECIES_VENIPEDE
	msgbox SafariZone_Text_ConfirmPoison, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, SafariZone_EventScript_TypeMenuPage1
	goto SafariZone_EventScript_GiveChosenStarter

SafariZone_EventScript_PickPsychic::
	setvar VAR_0x8004, SPECIES_SOLOSIS
	msgbox SafariZone_Text_ConfirmPsychic, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, SafariZone_EventScript_TypeMenuPage1
	goto SafariZone_EventScript_GiveChosenStarter

SafariZone_EventScript_PickRock::
	setvar VAR_0x8004, SPECIES_ARCHEN
	msgbox SafariZone_Text_ConfirmRock, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, SafariZone_EventScript_TypeMenuPage1
	goto SafariZone_EventScript_GiveChosenStarter

SafariZone_EventScript_PickSteel::
	setvar VAR_0x8004, SPECIES_HONEDGE
	msgbox SafariZone_Text_ConfirmSteel, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, SafariZone_EventScript_TypeMenuPage1
	goto SafariZone_EventScript_GiveChosenStarter

SafariZone_EventScript_PickWater::
	setvar VAR_0x8004, SPECIES_MUDKIP
	msgbox SafariZone_Text_ConfirmWater, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, SafariZone_EventScript_TypeMenuPage1
	goto SafariZone_EventScript_GiveChosenStarter

SafariZone_EventScript_GiveChosenStarter::
	givemon VAR_0x8004, 5
	goto_if_eq VAR_RESULT, FALSE, SafariZone_EventScript_PartyFull
	setflag FLAG_RECEIVED_SAFARI_STARTER
	msgbox SafariZone_Text_ReceivedStarter, MSGBOX_DEFAULT
	release
	end

SafariZone_EventScript_PartyFull::
	msgbox SafariZone_Text_PartyFull, MSGBOX_DEFAULT
	release
	end


SafariZone_Text_Intro:
	.string "Welcome to the SAFARI ZONE special\n"
	.string "partner promotion!\p"
	.string "I can offer you one POKéMON based on\n"
	.string "the type you choose.\p"
	.string "You may choose only one.\p"
	.string "Would you like to pick a partner?$"

SafariZone_Text_ChooseType:
	.string "Choose a type.$"

SafariZone_Text_NoThanks:
	.string "Very well.\p"
	.string "Come back if you change your mind.$"

SafariZone_Text_AlreadyPicked:
	.string "You already chose your partner,\n"
	.string "raise it well.\p"
	.string "Remember to visit the SAFARI ZONE!$"

SafariZone_Text_ReceivedStarter:
	.string "Take good care of your new partner!$"

SafariZone_Text_PartyFull:
	.string "Your party is full.\p"
	.string "Please come back with an open slot.$"

SafariZone_Text_ConfirmBug:
	.string "You want the BUG-Type SEWADDLE?$"

SafariZone_Text_ConfirmDark:
	.string "You want the DARK-Type PAWNIARD?$"

SafariZone_Text_ConfirmDragon:
	.string "You want the DRAGON-Type AXEW?$"

SafariZone_Text_ConfirmElectric:
	.string "You want the ELECTRIC-Type ELEKID?$"

SafariZone_Text_ConfirmFairy:
	.string "You want the FAIRY-Type TOGEPI?$"

SafariZone_Text_ConfirmFighting:
	.string "You want the FIGHTING-Type MACHOP?$"

SafariZone_Text_ConfirmFire:
	.string "You want the FIRE-Type FENNEKIN?$"

SafariZone_Text_ConfirmFlying:
	.string "You want the FLYING-Type ROOKIDEE?$"

SafariZone_Text_ConfirmGhost:
	.string "You want the GHOST-Type GASTLY?$"

SafariZone_Text_ConfirmGrass:
	.string "You want the GRASS-Type TURTWIG?$"

SafariZone_Text_ConfirmGround:
	.string "You want the GROUND-Type GLIGAR?$"

SafariZone_Text_ConfirmIce:
	.string "You want the ICE-Type SPHEAL?$"

SafariZone_Text_ConfirmNormal:
	.string "You want the NORMAL-Type MUNCHLAX?$"

SafariZone_Text_ConfirmPoison:
	.string "You want the POISON-Type VENIPEDE?$"

SafariZone_Text_ConfirmPsychic:
	.string "You want the PSYCHIC-Type SOLOSIS?$"

SafariZone_Text_ConfirmRock:
	.string "You want the ROCK-Type ARCHEN?$"

SafariZone_Text_ConfirmSteel:
	.string "You want the STEEL-Type HONEDGE?$"

SafariZone_Text_ConfirmWater:
	.string "You want the WATER-Type MUDKIP?$"

