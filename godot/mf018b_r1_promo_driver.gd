class_name MF018BR1PromoDriver
extends RefCounted

func smooth(value:float)->float:
	value=clampf(value,0.0,1.0);return value*value*(3.0-2.0*value)

func apply(scene:Node,time_value:float)->void:
	# Causal promo timeline only: lever -> gauges -> four-dot stages -> linked ring -> reactor.
	var startup:=smooth((time_value-1.15)/1.10)
	var gauge_wake:=smooth((time_value-1.75)/1.65)
	var dot_stage:=0.0
	if time_value>=2.75 and time_value<4.15:dot_stage=.08+.25*smooth((time_value-2.75)/1.40)
	elif time_value>=4.15 and time_value<5.45:dot_stage=.36+.30*smooth((time_value-4.15)/1.30)
	elif time_value>=5.45:dot_stage=.71+.29*smooth((time_value-5.45)/1.15)
	var linked:=smooth((time_value-5.72)/1.70)
	var reactor:=smooth((time_value-6.05)/4.25)
	var unstable:=smooth((time_value-9.0)/2.3);var critical:=smooth((time_value-11.5)/1.1)
	scene.set_startup_progress(startup);scene.set_indicator_stage(dot_stage);scene.set_linked_ring_activation(linked)
	scene.set_temperature(.08+.25*gauge_wake+.28*unstable+.24*critical)
	scene.set_containment(.84-.10*unstable-.24*critical)
	scene.set_field_strength(.05+.43*gauge_wake+.30*reactor+.12*critical)
	scene.set_pressure(.08+.20*gauge_wake+.34*unstable+.24*critical)
	scene.set_warning_level(.01+.14*linked+.42*unstable+.35*critical)
	scene.set_reactor_energy(.025+.18*linked+.46*reactor+.23*critical)
	scene.set_control_value("coolant_dial",.58-.16*critical);scene.set_control_value("field_dial",.16+.62*gauge_wake)
	var state:="DORMANT"
	if time_value>=11.5:state="CRITICAL"
	elif time_value>=9.0:state="UNSTABLE"
	elif time_value>=6.0:state="STABLE"
	scene.set_machine_state(state)
