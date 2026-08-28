class_name MF018BR1PulpScene
extends "res://mf018b_pulp_scene.gd"

signal startup_progress_changed(value:float)
signal indicator_stage_changed(value:float)
signal linked_ring_activation_changed(value:float)
signal startup_initiated()
signal yellow_trigger_reached()

var startup_progress:float=0.0
var indicator_stage:float=0.0
var linked_ring_activation:float=0.0

func _init()->void:
	# Parent renderer compatibility keys stay private; R1 exports only controls in its node tree.
	control_values={"coolant_dial":.58,"field_dial":.16,"containment_switch":0.0,"emergency_lever":0.0,"startup_lever":0.0}

func set_startup_progress(value:float)->void:
	var previous:=startup_progress;startup_progress=normalized(value);startup_progress_changed.emit(startup_progress)
	if previous<.05 and startup_progress>=.05:startup_initiated.emit();audio_event_requested.emit("startup_lever_clunk")

func set_indicator_stage(value:float)->void:
	var previous:=indicator_stage;indicator_stage=normalized(value);indicator_stage_changed.emit(indicator_stage)
	if previous<.70 and indicator_stage>=.70:yellow_trigger_reached.emit();audio_event_requested.emit("yellow_link_trigger")

func set_linked_ring_activation(value:float)->void:
	linked_ring_activation=normalized(value);linked_ring_activation_changed.emit(linked_ring_activation)

func set_control_value(id:String,value:float)->void:
	if id=="startup_lever":set_startup_progress(value);control_activated.emit(id,startup_progress);return
	super.set_control_value(id,value)

func activate_control(id:String)->void:
	if id=="startup_lever":set_control_value(id,0.0 if startup_progress>.5 else 1.0);return
	super.activate_control(id)

func state_snapshot()->Dictionary:
	var result:=super.state_snapshot();result["controls"]={"coolant_dial":control_values.coolant_dial,"field_dial":control_values.field_dial,"startup_lever":startup_progress};result["startup_progress"]=startup_progress;result["indicator_stage"]=indicator_stage;result["linked_ring_activation"]=linked_ring_activation;return result

func render_svg(time_value:float,camera_progress:float=0.0,diagnostic:bool=false)->String:
	var svg:=super.render_svg(time_value,camera_progress,false).trim_suffix("</svg>")
	# Rebuild the complete upper collar as two deliberately separated native tracks.
	# Eighteen small fixed details occupy the outer track; six linked indicators occupy the inner upper track.
	svg+="<g id='r1_clean_ring'><ellipse cx='526' cy='286' rx='186' ry='94' fill='#102a25' stroke='#e6b905' stroke-width='11'/><ellipse cx='526' cy='286' rx='154' ry='66' fill='#173f36' stroke='#d2b862' stroke-width='6'/><ellipse cx='526' cy='286' rx='130' ry='44' fill='#173f36' stroke='#f0d58f' stroke-width='4'/>"
	for detail in range(18):
		var detail_angle:=TAU*float(detail)/18.0;var detail_x:=526.0+cos(detail_angle)*170.0;var detail_y:=286.0+sin(detail_angle)*79.0
		svg+="<circle class='small-ring-detail' cx='%.1f' cy='%.1f' r='4' fill='#08100e' stroke='#f0d58f' stroke-width='2'/>" % [detail_x,detail_y]
	for indicator in range(6):
		var indicator_angle:=PI+PI*(float(indicator)+.5)/6.0;var indicator_x:=526.0+cos(indicator_angle)*137.0;var indicator_y:=286.0+sin(indicator_angle)*48.0
		var activation:=clampf(linked_ring_activation*6.0-float(indicator),0.0,1.0)
		svg+="<circle class='linked-ring-housing' cx='%.1f' cy='%.1f' r='12' fill='#251a0d' stroke='#d2b862' stroke-width='3'/>" % [indicator_x,indicator_y]
		if activation>.01:
			svg+="<circle cx='%.1f' cy='%.1f' r='21' fill='url(#redglow)' opacity='%.3f'/><circle class='linked-ring-bulb' cx='%.1f' cy='%.1f' r='7' fill='#e99019' opacity='%.3f'/>" % [indicator_x,indicator_y,activation,indicator_x,indicator_y,.35+.65*activation]
	svg+="</g>"
	# Clean the lower console panel. The passive containment-switch detail is intentionally absent.
	svg+="<path id='r1_control_panel_clean' d='M57 744 L224 744 L235 947 L52 975 Z' fill='#0a1a17' stroke='#40756a' stroke-width='3'/><path d='M68 752 H219' stroke='#9b8345' stroke-width='3'/>"
	for dial in range(2):
		var dial_x:=91.0+dial*72.0;var dial_value:=float(control_values[["coolant_dial","field_dial"][dial]]);var dial_angle:=deg_to_rad(135.0+270.0*dial_value)
		svg+="<circle cx='%.1f' cy='806' r='23' fill='#1d2923' stroke='#c3a250' stroke-width='5'/><path d='M%.1f 806 L%.1f %.1f' stroke='#f1d68c' stroke-width='4'/>" % [dial_x,dial_x,dial_x+cos(dial_angle)*16.0,806+sin(dial_angle)*16.0]
	# The red-knob lever rotates from vertical to approximately ninety degrees right.
	var lever_angle:=deg_to_rad(-90.0+90.0*startup_progress);var pivot_x:=174.0;var pivot_y:=864.0;var tip_x:=pivot_x+cos(lever_angle)*43.0;var tip_y:=pivot_y+sin(lever_angle)*43.0
	svg+="<circle class='startup-lever-pivot' cx='%.1f' cy='%.1f' r='19' fill='#101d19' stroke='#b99b4b' stroke-width='4'/><path class='startup-lever-arm' d='M%.1f %.1f L%.1f %.1f' stroke='#b99b4b' stroke-width='8'/><circle class='startup-lever-red-knob' cx='%.1f' cy='%.1f' r='11' fill='#c72d1d'/>" % [pivot_x,pivot_y,pivot_x,pivot_y,tip_x,tip_y,tip_x,tip_y]
	# Four evenly spaced indicators stay inside the panel and progress blue, green, then yellow.
	var dot_color:="#247fc4";var active_count:=int(ceil(clampf(indicator_stage/.34,0.0,1.0)*4.0))
	if indicator_stage>=.70:dot_color="#e6b905";active_count=4
	elif indicator_stage>=.34:dot_color="#3aa75b";active_count=int(ceil(1.0+clampf((indicator_stage-.34)/.36,0.0,1.0)*3.0))
	for dot in range(4):
		var dot_x:=70.0+dot*46.0;svg+="<circle class='four-dot-housing' cx='%.1f' cy='921' r='11' fill='#15150e' stroke='#c3a250' stroke-width='3'/>" % dot_x
		if dot<active_count and indicator_stage>.01:svg+="<circle class='four-dot-active' cx='%.1f' cy='921' r='7' fill='%s'/>" % [dot_x,dot_color]
	if diagnostic:
		svg+="<rect x='25' y='135' width='300' height='175' fill='#03100f' stroke='#4ee6ff' stroke-width='3'/><circle cx='174' cy='864' r='26' fill='none' stroke='#4ee6ff' stroke-width='3'/><circle cx='139' cy='921' r='65' fill='none' stroke='#4ee6ff' stroke-width='3'/><ellipse cx='526' cy='286' rx='151' ry='62' fill='none' stroke='#4ee6ff' stroke-width='3'/></g>"
	svg+="</svg>";return svg
