class_name MF018BPromoDriver
extends RefCounted

const DURATION := 14.0

func smooth(value:float)->float:
	value=clampf(value,0.0,1.0)
	return value*value*(3.0-2.0*value)

func apply(scene:Node,time_value:float)->void:
	# Promo-only policy. The base scene contains no timeline or game rules.
	var wake:=smooth((time_value-1.4)/2.2)
	var stable:=smooth((time_value-3.2)/2.0)
	var unstable:=smooth((time_value-7.0)/2.3)
	var critical:=smooth((time_value-11.1)/1.1)
	scene.set_reactor_energy(.03+.28*wake+.30*stable+.24*unstable+.13*critical)
	scene.set_temperature(.12+.18*wake+.28*unstable+.30*critical)
	scene.set_containment(.82-.12*unstable-.24*critical)
	scene.set_field_strength(.08+.42*stable+.32*unstable+.12*critical)
	scene.set_pressure(.10+.18*stable+.35*unstable+.25*critical)
	scene.set_warning_level(.02+.18*stable+.42*unstable+.36*critical)
	scene.set_control_value("coolant_dial",.56-.18*critical)
	scene.set_control_value("field_dial",.18+.62*stable)
	scene.set_control_value("containment_switch",1.0 if time_value>=3.0 else 0.0)
	scene.set_control_value("emergency_lever",1.0 if time_value>=11.1 else 0.0)
	var state:="DORMANT"
	if time_value>=11.1:state="CRITICAL"
	elif time_value>=7.0:state="UNSTABLE"
	elif time_value>=3.2:state="STABLE"
	scene.set_machine_state(state)
