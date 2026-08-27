extends "res://indicator_pulse_stage.gd"

## MF-012: bounded, subject-agnostic visual activity choreography.

const ACTIVITY_TYPES := [
	"target_acquire", "target_move", "target_escape", "target_reacquire", "tracker_converge", "target_lock",
	"fragment_spawn", "fragment_drift", "fragment_align", "record_reconstruct",
	"connection_attempt", "signal_travel", "bridge_form", "bridge_stabilize",
	"path_override", "network_reroute", "anomaly_seed", "cascade_failure"
]
const ACTIVITY_FAMILY := {
	"target_acquire":"pursuit", "target_move":"pursuit", "target_escape":"pursuit",
	"target_reacquire":"pursuit", "tracker_converge":"pursuit", "target_lock":"pursuit",
	"fragment_spawn":"reconstruction", "fragment_drift":"reconstruction",
	"fragment_align":"reconstruction", "record_reconstruct":"reconstruction",
	"connection_attempt":"connection", "signal_travel":"connection",
	"bridge_form":"connection", "bridge_stabilize":"connection",
	"path_override":"override", "network_reroute":"override",
	"anomaly_seed":"cascade_failure", "cascade_failure":"cascade_failure"
}
const DEPENDENCIES := {
	"target_move":["target_acquire"], "target_escape":["target_move"],
	"target_reacquire":["target_escape"], "tracker_converge":["target_reacquire"],
	"target_lock":["target_acquire", "target_reacquire"],
	"fragment_drift":["fragment_spawn"], "fragment_align":["fragment_drift"],
	"record_reconstruct":["fragment_align"],
	"signal_travel":["connection_attempt"], "bridge_form":["connection_attempt", "signal_travel"],
	"bridge_stabilize":["bridge_form"], "network_reroute":["path_override"],
	"cascade_failure":["anomaly_seed"]
}
const OPENINGS := [
	"cold_open_active_record", "signal_intrusion", "slow_system_wake", "target_already_moving",
	"corrupt_record_resolve", "warning_state_open", "single_cell_propagation", "follow_energy_packet",
	"network_overload_open", "projection_from_darkness"
]
const ACTIVITY_CAMERAS := [
	"static", "slow_push", "pull_back", "lateral_track", "follow_packet", "orbit_subtle",
	"close_to_wide", "wide_to_close", "reveal_from_detail"
]
const ANCHORS := {
	"west_bus":Vector2(-315,-70), "east_bus":Vector2(315,85), "north_bus":Vector2(0,-470),
	"south_bus":Vector2(0,455), "primary_target":Vector2(-155,-115), "tracker_field":Vector2(0,-95),
	"primary_record":Vector2(0,-120), "fragment_field":Vector2(0,-115), "node_a":Vector2(-205,105),
	"node_b":Vector2(205,105), "circuit_network":Vector2(0,80), "wall_cells":Vector2(0,-10),
	"central_hub":Vector2(0,125), "survivor_path":Vector2(255,320)
}

var activity:Dictionary={}
var activity_enabled:=false
var activity_sequence:Array=[]
var observed_activity:Dictionary={}

func configure(source_fixture:Dictionary,source_timeline:Dictionary,source_layouts:Dictionary,source_heavy:Font,source_regular:Font)->Dictionary:
	var result:=super.configure(source_fixture,source_timeline,source_layouts,source_heavy,source_regular)
	if result.get("result")!="PASS":return result
	activity=source_fixture.get("activity",{})
	if activity.is_empty():return {"result":"FAIL","error":"MF012_ACTIVITY_SEQUENCE_MISSING"}
	var dominant:=str(activity.get("dominant_activity",""))
	var supporting:Array=activity.get("supporting_activities",[])
	if dominant not in ["pursuit","reconstruction","connection","override","cascade_failure"]:
		return {"result":"FAIL","error":"MF012_DOMINANT_ACTIVITY_UNKNOWN: "+dominant}
	if supporting.size()>2:return {"result":"FAIL","error":"MF012_ACTIVITY_COMPLEXITY_EXCEEDED"}
	if str(activity.get("opening_choreography","")) not in OPENINGS:
		return {"result":"FAIL","error":"MF012_OPENING_CHOREOGRAPHY_UNKNOWN"}
	if str(activity.get("camera_choreography","")) not in ACTIVITY_CAMERAS:
		return {"result":"FAIL","error":"MF012_CAMERA_CHOREOGRAPHY_UNKNOWN"}
	var targets:Array=activity.get("targets",[])
	activity_sequence=activity.get("sequence",[])
	if activity_sequence.is_empty():return {"result":"FAIL","error":"MF012_ACTIVITY_SEQUENCE_MISSING"}
	var seen:Array=[]
	var previous_start:float=-1.0
	for entry in activity_sequence:
		var activity_type:=str(entry.get("type",""))
		if activity_type not in ACTIVITY_TYPES:return {"result":"FAIL","error":"UNKNOWN_ACTIVITY: "+activity_type}
		var target:=str(entry.get("target",""))
		if target.is_empty() or target not in targets or not ANCHORS.has(target):
			return {"result":"FAIL","error":"MF012_ACTIVITY_TARGET_INVALID: "+target}
		var start:=float(entry.get("start",-1.0));var span:=float(entry.get("duration",0.0))
		var intensity:=float(entry.get("intensity",1.0));var repeat_count:=int(entry.get("repeat",1))
		if start<0 or span<=0 or start+span>duration or intensity<0.1 or intensity>1.0 or repeat_count<1 or repeat_count>4:
			return {"result":"FAIL","error":"MF012_ACTIVITY_TIMING_INVALID: "+str(entry.get("id",activity_type))}
		if start<previous_start:return {"result":"FAIL","error":"MF012_ACTIVITY_SEQUENCE_ORDER_INVALID"}
		previous_start=start
		for dependency in DEPENDENCIES.get(activity_type,[]):
			if dependency not in seen:return {"result":"FAIL","error":"MF012_ACTIVITY_DEPENDENCY_INVALID: %s requires %s"%[activity_type,dependency]}
		seen.append(activity_type)
		if ACTIVITY_FAMILY[activity_type]!=dominant and ACTIVITY_FAMILY[activity_type] not in supporting:
			return {"result":"FAIL","error":"MF012_ACTIVITY_FAMILY_OUTSIDE_BUDGET: "+activity_type}
	activity_enabled=true
	return {"result":"PASS"}

func set_story_time(value:float)->void:
	super.set_story_time(value)
	if not activity_enabled:return
	for entry in activity_sequence:
		if value>=float(entry.start):observed_activity[str(entry.id)]={"type":str(entry.type),"time":float(entry.start),"observed_frame":int(round(value*30.0))}
	var progress:=clampf(value/maxf(duration,.1),0,1)
	var camera:=str(activity.camera_choreography)
	var factor:=1.0;var lateral:=0.0;var vertical:=0.0;var angle:=-.3
	if camera=="slow_push":factor=.96+progress*.09
	elif camera=="pull_back":factor=1.08-progress*.13
	elif camera=="lateral_track":lateral=sin(progress*PI*1.2)*34.0;factor=1.025
	elif camera=="follow_packet":lateral=lerp(-34.0,34.0,_smooth(progress));vertical=sin(progress*PI)*-15.0;factor=1.07
	elif camera=="orbit_subtle":lateral=sin(progress*TAU)*20.0;vertical=cos(progress*TAU)*9.0;angle=-.3+sin(progress*TAU)*.45
	elif camera=="close_to_wide":factor=1.11-progress*.16
	elif camera=="wide_to_close":factor=.92+progress*.17
	elif camera=="reveal_from_detail":factor=1.16-_smooth(progress)*.19;lateral=lerp(28.0,0.0,_smooth(progress))
	position=Vector2(270+lateral,480+vertical);scale=Vector2.ONE*factor;rotation=deg_to_rad(angle);queue_redraw()

func validation_report()->Dictionary:
	var report:=super.validation_report()
	var evidence:=[];var all_observed:=true
	for entry in activity_sequence:
		var found:=observed_activity.has(str(entry.id));all_observed=all_observed and found
		evidence.append({"id":entry.id,"type":entry.type,"start":entry.start,"duration":entry.duration,
			"status":"PASS" if found else "NOT_RUN","observed":observed_activity.get(str(entry.id),null)})
	report.strategy="godot_activity_vocabulary_v1"
	report.activity_vocabulary={"version":1,"primitive_count":ACTIVITY_TYPES.size(),"primitives":ACTIVITY_TYPES,
		"dominant_activity":activity.get("dominant_activity"),"supporting_activities":activity.get("supporting_activities",[]),
		"opening_choreography":activity.get("opening_choreography"),"camera_choreography":activity.get("camera_choreography"),
		"targets":activity.get("targets",[]),"event_evidence":evidence,"all_observed":all_observed,
		"subject_agnostic":true,"deterministic":true,"seed":int(fixture.seed),"result":"PASS" if all_observed else "FAIL"}
	return report

func _draw()->void:
	super._draw()
	if activity_enabled:_draw_activity_layer()

func _draw_activity_layer()->void:
	var opening_alpha:=_smooth(_ramp(current_time,0.0,.45))
	_draw_activity_header(opening_alpha)
	match str(activity.dominant_activity):
		"pursuit":_draw_pursuit_activity()
		"reconstruction":_draw_reconstruction_activity()
		"connection":_draw_connection_activity()
		"override":_draw_override_activity()
		"cascade_failure":_draw_cascade_activity()

func _draw_activity_header(alpha:float)->void:
	var dominant:=str(activity.dominant_activity).replace("_"," ").to_upper()
	draw_rect(Rect2(-318,-512,220,30),Color(.015,.06,.07,.72*alpha),true)
	draw_string(regular_font,Vector2(-306,-491),"ACTIVITY // "+dominant,HORIZONTAL_ALIGNMENT_LEFT,-1,13,Color(.42,1,.88,.86*alpha))
	var latest:Dictionary={}
	for entry in activity_sequence:
		if current_time>=float(entry.start):latest=entry
	if not latest.is_empty():
		var label:=str(latest.type).replace("_"," ").to_upper()
		draw_string(regular_font,Vector2(-306,493),label,HORIZONTAL_ALIGNMENT_LEFT,-1,13,Color(.96,.65,.29,.9))

func _entry(activity_type:String)->Dictionary:
	var found:Dictionary={}
	for entry in activity_sequence:
		if str(entry.type)==activity_type:found=entry
	return found

func _progress(activity_type:String)->float:
	var entry:=_entry(activity_type)
	if entry.is_empty():return 0.0
	return _smooth(clampf((current_time-float(entry.start))/maxf(.01,float(entry.duration)),0,1))

func _active(activity_type:String)->bool:
	var entry:=_entry(activity_type)
	return not entry.is_empty() and current_time>=float(entry.start)

func _anchor(name:String)->Vector2:
	return ANCHORS.get(name,Vector2.ZERO)

func _draw_pursuit_activity()->void:
	var acquire:=_progress("target_acquire");var move:=_progress("target_move");var escape:=_progress("target_escape")
	var reacquire:=_progress("target_reacquire");var converge:=_progress("tracker_converge");var lock:=_progress("target_lock")
	var start:=Vector2(-220,-40);var finish:=Vector2(210,-165);var target:=start.lerp(finish,move)
	if escape>0 and reacquire<=0:target+=Vector2(120,-80)*escape
	if reacquire>0:target=Vector2(185,15).lerp(Vector2(95,-115),reacquire)
	var visibility:=acquire*(1.0-escape)+reacquire
	if visibility>.01:
		draw_circle(target,8+reacquire*4,Color(1,.38,.22,.88*clampf(visibility,0,1)))
		draw_arc(target,18+lock*8,0,TAU,20,Color(1,.72,.34,.72),3)
	for index in range(4):
		var origin:Vector2=[Vector2(-315,-300),Vector2(315,-260),Vector2(-315,270),Vector2(315,315)][index]
		var aim:=origin.lerp(target,converge)
		var overshoot:=Vector2((index-1.5)*18.0,(-1 if index%2 else 1)*24.0)*(1.0-converge)
		draw_line(origin,aim+overshoot,Color(1,.3,.2,.22+.52*converge),3)
	if lock>.02:
		for corner in [Vector2(-1,-1),Vector2(1,-1),Vector2(1,1),Vector2(-1,1)]:
			draw_line(target+corner*30,target+corner*18,Color(1,.76,.38,.9*lock),4)

func _fragment_origin(index:int)->Vector2:
	var angle:=float((index*83+int(fixture.seed))%360)*PI/180.0
	var radius:=150.0+float((index*37)%150)
	return Vector2(cos(angle)*radius,sin(angle)*radius-70)

func _fragment_destination(index:int)->Vector2:
	return Vector2(-150+(index%6)*58,-225+int(index/6)*70)

func _draw_reconstruction_activity()->void:
	var spawn:=_progress("fragment_spawn");var drift:=_progress("fragment_drift");var align:=_progress("fragment_align");var resolved:=_progress("record_reconstruct")
	for index in range(18):
		var delay:=float(index%6)*.07;var local:=clampf(spawn-delay,0,1)
		var point:=_fragment_origin(index).lerp(_fragment_origin(index)*.72,drift)
		point=point.lerp(_fragment_destination(index),align)
		var color:=Color(.38,.95,.84,(.25+.7*local)*(1.0-resolved*.65))
		draw_rect(Rect2(point,Vector2(20+index%4*5,9+index%3*4)),color,true)
	if resolved>0:
		draw_rect(Rect2(-178,-260,356,265),Color(.02,.12,.13,.72*resolved),true)
		draw_rect(Rect2(-178,-260,356,265),Color(.34,1,.88,.9*resolved),false,5)
		draw_string(heavy_font,Vector2(-145,-112),"RECORD RECONSTRUCTED",HORIZONTAL_ALIGNMENT_LEFT,-1,22,Color(.86,1,.95,resolved))

func _draw_connection_activity()->void:
	var attempt:=_progress("connection_attempt");var travel:=_progress("signal_travel");var formed:=_progress("bridge_form");var stable:=_progress("bridge_stabilize")
	var left:=_anchor("node_a");var right:=_anchor("node_b")
	draw_circle(left,13+sin(current_time*3)*3,Color(.36,1,.78,.9));draw_circle(right,13+cos(current_time*2.6)*3,Color(.42,.64,1,.9))
	for segment in range(8):
		if (segment+int(current_time*8))%3!=0 or formed>.1:
			var a:=left.lerp(right,float(segment)/8.0);var b:=left.lerp(right,float(segment+1)/8.0)
			draw_line(a,b,Color(.4,.86,1,.2+.65*maxf(attempt,formed)),2+stable*3)
	if travel>0:
		for packet in range(4):
			var point:=left.lerp(right,fmod(travel+packet*.21,1.0));draw_circle(point,5,Color(.78,1,.94,.95))
	for cell in range(6):
		var response:=clampf(stable*1.4-float(cell)*.13,0,1);var point:=Vector2(-270+cell*108,330+sin(cell)*25)
		draw_rect(Rect2(point-Vector2(25,18),Vector2(50,36)),Color(.25,.9,.75,.28*response),true)

func _draw_override_activity()->void:
	var override:=_progress("path_override");var reroute:=_progress("network_reroute")
	var routes:Array=[
		[Vector2(-330,-330),Vector2(-210,-330),Vector2(-210,-40),NODE],
		[Vector2(330,-250),Vector2(235,-250),Vector2(235,20),NODE],
		[Vector2(-330,330),Vector2(-125,330),Vector2(-125,215),NODE],
		[Vector2(330,355),Vector2(150,355),Vector2(150,245),NODE]
	]
	for index in range(routes.size()):
		var shift:=clampf(reroute*1.5-float(index)*.18,0,1)
		_draw_partial_path(routes[index],1.0,Color("dc5c42").lerp(Color("f0a044"),shift),3+shift*4)
		if shift>0:
			var point:=_point_on_path(routes[index],fmod(current_time*.42+index*.19,1.0));draw_circle(point,6,Color(1,.8,.35,.95))
	var intrusion:=Vector2(-335,-430).lerp(NODE,override)
	draw_circle(intrusion,8+override*6,Color(1,.38,.2,.9))
	draw_string(heavy_font,Vector2(-145,315),"CONTROL ROUTE REPLACED",HORIZONTAL_ALIGNMENT_LEFT,-1,20,Color(1,.67,.3,.85*reroute))

func _draw_cascade_activity()->void:
	var anomaly:=_progress("anomaly_seed");var failure:=_progress("cascade_failure")
	var nodes:Array=[Vector2(-245,-270),Vector2(-110,-185),Vector2(35,-265),Vector2(190,-150),Vector2(-220,105),Vector2(140,195),Vector2(265,315)]
	for index in range(nodes.size()):
		var local:=clampf(failure*1.5-float(index)*.13,0,1);var point:Vector2=nodes[index]
		draw_line(NODE,point,Color(.25,.7,.68,.35*(1.0-local)),3)
		draw_circle(point,10,Color(.28,.88,.76,.55*(1.0-local)))
		if local>.08:
			draw_line(point-Vector2(12,12),point+Vector2(12,12),Color(1,.28,.18,.9*local),5)
			draw_line(point+Vector2(-12,12),point+Vector2(12,-12),Color(1,.28,.18,.9*local),5)
	if anomaly>0:
		draw_circle(nodes[0],18+anomaly*16,Color(1,.25,.16,.18));draw_arc(nodes[0],25+anomaly*25,0,TAU,24,Color(1,.48,.22,.8),4)
	if failure>.65:
		var survivor:Array=[Vector2(330,390),Vector2(250,390),Vector2(250,285),Vector2(90,285),NODE]
		_draw_partial_path(survivor,clampf((failure-.65)/.35,0,1),Color(.45,1,.75,.95),6)
		draw_string(heavy_font,Vector2(55,340),"SURVIVOR PATH",HORIZONTAL_ALIGNMENT_LEFT,-1,19,Color(.55,1,.8,.9))
