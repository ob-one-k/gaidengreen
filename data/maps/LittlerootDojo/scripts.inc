LittlerootDojo_MapScripts::
	.byte 0

Dojo_EventScript_Lyle::
    lock
    faceplayer

    goto_if_unset FLAG_SENSEI_UNLOCKED, Littleroot_Sensei_NotReady

    // Already beaten
    goto_if_set FLAG_SENSEI_DEFEATED, Littleroot_Sensei_After

    // Ready to battle
    msgbox Littleroot_Sensei_Intro_Text, MSGBOX_DEFAULT
    closemessage

    goto Littleroot_Sensei_Battle

Littleroot_Sensei_NotReady::
    msgbox Littleroot_Sensei_NotReady_Text, MSGBOX_DEFAULT
    release
    end

Littleroot_Sensei_Battle::
    trainerbattle_no_intro TRAINER_LYLE, Littleroot_Sensei_Defeat_Text

    setflag FLAG_SENSEI_DEFEATED

    msgbox Littleroot_Sensei_Win_Text, MSGBOX_DEFAULT

    release
    end

Littleroot_Sensei_After::
    msgbox Littleroot_Sensei_Repeat_Text, MSGBOX_DEFAULT
    release
    end

Dojo_EventScript_KirliaPC::
    lock
    faceplayer

    msgbox Dojo_KirliaPC_Text, MSGBOX_DEFAULT

    goto EventScript_PC

Littleroot_Sensei_Intro_Text:
    .string "So you've come.\nShow me your strength.$"

Littleroot_Sensei_Win_Text:
    .string "Good.\nNow you are ready for the gym.\p"
    .string "YOUR LEVEL CAP HAS INCREASED\nYou new level cap is 17.$"

Littleroot_Sensei_Repeat_Text:
    .string "You've already proven yourself.$"

Littleroot_Sensei_Defeat_Text:
    .string "Impressive… You have grown.$"

Littleroot_Sensei_NotReady_Text:
    .string "You are not ready.\n"
    .string "Go to Rustboro and then comeback.$"

Dojo_KirliaPC_Text:
    .string "Kirlia tilts its head...\n"
    .string "It seems to connect you to a PC.$"
