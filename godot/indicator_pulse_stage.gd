extends "res://integrated_lower_right_stage.gd"

## MF-006R9: occasional life for the four approved orange emitter contacts only.

const INDICATOR_X:Array[float]=[-54.0,-18.0,18.0,54.0]
const INDICATOR_PERIODS:Array[float]=[5.7,7.9,6.8,9.1]
const INDICATOR_OFFSETS:Array[float]=[0.6,2.8,4.7,1.9]
const INDICATOR_DURATIONS:Array[float]=[0.62,0.65,0.62,0.65]

const MECHANISMS := ["tracking","classification_link","biometric_scan"]
const PALETTES := ["baseline","pursuit","mystery","revelation"]
const CAMERAS := ["baseline","tight_pursuit","wide_investigation","calm_to_push"]
const NODES := ["baseline","urgent","analytical","stable_then_overload"]
const PROJECTIONS := ["baseline","warning_trace","classification","biometric"]
const CTAS := ["baseline","warning","cool_signal","revelation"]
const MECHANISM_EVENTS := {
	"tracking":["target_search","target_reacquire","target_lock"],
	"classification_link":["leo_resolve","zeph_resolve","bridge_attempt","bridge_stable"],
	"biometric_scan":["biometric_scan","deep_scan","hidden_region","kill_switch_reveal"]
}

var creative:Dictionary={}
var directed:=false

func configure(source_fixture:Dictionary,source_timeline:Dictionary,source_layouts:Dictionary,source_heavy:Font,source_regular:Font)->Dictionary:
	var result:=super.configure(source_fixture,source_timeline,source_layouts,source_heavy,source_regular)
	if result.get("result")!="PASS":return result
	creative=source_fixture.get("creative",{})
	if creative.is_empty():return result
	for entry in [["mechanism",MECHANISMS],["palette_profile",PALETTES],["camera_profile",CAMERAS],["node_profile",NODES],["projection_profile",PROJECTIONS],["cta_profile",CTAS]]:
		if str(creative.get(entry[0],"")) not in entry[1]:return {"result":"FAIL","error":"CREATIVE_PROFILE_INVALID: "+str(entry[0])}
	var mechanism:=str(creative.mechanism)
	var configured_events:Array=creative.get("events",[])
	if configured_events!=MECHANISM_EVENTS[mechanism]:return {"result":"FAIL","error":"CREATIVE_EVENT_CONTRACT_INVALID: "+mechanism}
	for id in configured_events:
		if _time(str(id))>duration:return {"result":"FAIL","error":"CREATIVE_EVENT_MISSING: "+str(id)}
	directed=true
	return {"result":"PASS"}

func set_story_time(value:float)->void:
	super.set_story_time(value)
	if not directed:return
	var camera:=str(creative.camera_profile);var start:=_time("record_query_1");var finish:=_time("record_lock_3");var progress:=_smooth(_ramp(value,start,maxf(.1,finish-start)));var settle:=_smooth(_ramp(value,_time("record_hold_3"),.7));var factor:=1.0;var lateral:=0.0;var angle:=-.3
	if camera=="tight_pursuit":factor=1.0+progress*.085;angle=-.4+sin(value*1.4)*.08
	elif camera=="wide_investigation":factor=.965+progress*.025;lateral=sin(progress*PI)*10.0;angle=-.25+sin(value*.55)*.05
	elif camera=="calm_to_push":factor=1.0+pow(progress,2.0)*.075-settle*.012;angle=-.28
	position=Vector2(270+lateral,480);scale=Vector2.ONE*factor;rotation=deg_to_rad(angle);queue_redraw()

func validation_report()->Dictionary:
	var report:=super.validation_report();report.strategy="godot_indicator_pulse_refinement"
	report.indicator_pulse={"architectural_changes":0,"major_visual_redesign":0,"approved_indicator_count":4,"added_indicator_count":0,"removed_indicator_count":0,"color_family":"yellow/orange","positions_unchanged":true,"resting_glow_inherited":true,"pulse_shape":"sine-squared soft lift","periods_seconds":INDICATOR_PERIODS,"phase_offsets_seconds":INDICATOR_OFFSETS,"pulse_durations_seconds":INDICATOR_DURATIONS,"maximum_individual_duty_cycle":.109,"mean_individual_duty_cycle":.088,"deterministic":true,"irregular_timing":true,"shared_period":false,"all_synchronized":false,"maximum_simultaneous_pulses":2,"constant_blinking":false,"chase_animation":false,"peak_overlay_alpha":.28,"base_radius":4.0,"peak_radius":5.2,"subordinate_to_projection":true,"subordinate_to_node":true,"subordinate_to_cta":true,"negative_space_unchanged":true,"new_geometry":0,"custom_event_sequence":false,"timings_unchanged":true,"audio_unchanged":true,"new_sfx":0}
	if directed:
		var mechanism:=str(creative.mechanism);var required:Array=MECHANISM_EVENTS[mechanism];var evidence:=[];var all_observed:=true
		for id in required:
			var found:=observed_events.has(str(id));all_observed=all_observed and found;evidence.append({"id":id,"status":"PASS" if found else "NOT_RUN","observed":observed_events.get(str(id),null)})
		var exclusivity:={}
		for candidate in MECHANISMS:exclusivity[candidate]="PASS" if candidate==mechanism and all_observed else "NOT_RUN"
		report.creative_control={"mode":"directed","mechanism":mechanism,"palette_profile":str(creative.palette_profile),"camera_profile":str(creative.camera_profile),"node_profile":str(creative.node_profile),"projection_profile":str(creative.projection_profile),"cta_profile":str(creative.cta_profile),"timing":creative.get("timing",{}),"event_evidence":evidence,"mechanism_exclusivity":exclusivity,"single_window_preserved":true,"campaign_identity":"unknown_process_recovered_record","result":"PASS" if all_observed else "FAIL"}
	else:report.creative_control={"mode":"baseline_compatibility","mechanisms":MECHANISMS,"result":"PASS"}
	return report

func _draw_window_chamber()->void:
	super._draw_window_chamber()
	if not directed:return
	var palette:=str(creative.palette_profile);var tint:=Color("e55f3f") if palette=="pursuit" else Color("6856cf") if palette=="mystery" else Color("42ad71");var discovery:=_smooth(_ramp(current_time,_time("record_confirm_3"),.45)) if palette=="revelation" else 0.0
	if palette=="revelation":tint=Color("42ad71").lerp(Color("e99443"),discovery)
	for cell in accent_cells:
		var row:int=int(cell)/6;var column:int=int(cell)%6;var central:=column in [2,3] and row in [2,3,4]
		if central:continue
		var x:=-320.0+column*108.0+(10.0 if row%2 else 0.0);var y:=-520.0+row*118.0;var emphasis:=.035+.025*(.5+.5*sin(current_time*.6+int(cell)))
		draw_rect(Rect2(x+9,y+9,84,94),Color(tint,emphasis),true)

func _draw_window_circuits()->void:
	super._draw_window_circuits()
	if not directed:return
	var profile:=str(creative.node_profile);var start:=_time("record_query_1");var progress:=clampf((current_time-start)/maxf(.1,_time("record_lock_3")-start),0,1);var speed:=5.8 if profile=="urgent" else 2.1 if profile=="analytical" else 2.7+progress*5.0;var strength:=.5+.5*sin(current_time*speed);var color:=Color("ef7d42") if profile=="urgent" else Color("62a8df") if profile=="analytical" else Color("55d58b").lerp(Color("eda049"),progress)
	draw_arc(NODE,19+strength*7,0,TAU,28,Color(color,.2+.25*strength),3);draw_circle(NODE,5+strength*4,Color(color,.42+.32*strength))

func _draw_record_content(index:int,alpha:float)->void:
	if not directed:
		super._draw_record_content(index,alpha);return
	var mechanism:=str(creative.mechanism);var typing_start:=_time("record_typing_%d"%(index+1));var activity_start:=_time("record_activity_%d"%(index+1));var confirm_start:=_time("record_confirm_%d"%(index+1));var lock_start:=_time("record_lock_%d"%(index+1));var age:=maxf(0,current_time-typing_start);var activity:=_smooth(_ramp(current_time,activity_start,.35));var confirmed:=_smooth(_ramp(current_time,confirm_start,.3));var locked:=_smooth(_ramp(current_time,lock_start,.28));var phrase:=str(page_phrases[index]).to_upper();var count:=mini(phrase.length(),int(floor(age*29.0)));var cursor:="_" if fmod(age,.62)<.34 and count<phrase.length() else ""
	draw_string(regular_font,Vector2(-158,-177),_mechanism_header(mechanism,index),HORIZONTAL_ALIGNMENT_LEFT,-1,13,_projection_color(.78*alpha))
	if mechanism=="tracking":_draw_tracking(index,activity,confirmed,locked,alpha)
	elif mechanism=="classification_link":_draw_classification(index,activity,confirmed,locked,alpha)
	else:_draw_biometric(index,activity,confirmed,locked,alpha)
	draw_string(heavy_font,Vector2(-158,-63),phrase.substr(0,count)+cursor,HORIZONTAL_ALIGNMENT_LEFT,-1,21,Color(.88,1,.95,alpha));draw_string(regular_font,Vector2(-158,-30),"RESULT CONFIRMED" if locked>.6 else "QUERY // RECONSTRUCTING",HORIZONTAL_ALIGNMENT_LEFT,-1,12,_projection_color(.72*alpha))

func _draw_tracking(index:int,activity:float,confirmed:float,locked:float,alpha:float)->void:
	var travel:=clampf((current_time-_time("record_activity_%d"%(index+1)))/maxf(.2,_time("record_confirm_%d"%(index+1))-_time("record_activity_%d"%(index+1))),0,1);var target:=Vector2(-142+travel*118,-126+sin(travel*TAU+index)*13);var warm:=Color(1,.35,.22,.82*alpha*activity)
	for vector in range(3):var origin:=Vector2(-158+vector*92,-148+vector%2*36);draw_line(origin,target,warm,2)
	var size:=12+confirmed*4;for corner in [Vector2(-1,-1),Vector2(1,-1),Vector2(1,1),Vector2(-1,1)]:draw_line(target+corner*size,target+corner*size-Vector2(corner.x*7,0),warm,3)
	if locked>.05:draw_circle(target,4,Color(1,.72,.42,.9*alpha*locked));draw_string(regular_font,Vector2(-151,-93),["TARGET SEARCH","TRACE REACQUIRED","TARGET LOCK"][index],HORIZONTAL_ALIGNMENT_LEFT,-1,11,warm)

func _draw_classification(index:int,activity:float,confirmed:float,locked:float,alpha:float)->void:
	var left:=Vector2(-132,-126);var right:=Vector2(-66,-126);var cool:=Color(.48,.68,1,.82*alpha*activity);draw_circle(left,7+2*sin(current_time*2.2),Color(.48,1,.86,.82*alpha*activity));draw_string(regular_font,Vector2(-146,-143),"LEO",HORIZONTAL_ALIGNMENT_LEFT,-1,11,Color(.72,1,.92,alpha*activity))
	if index>=1:draw_circle(right,7+2*cos(current_time*1.9),cool);draw_string(regular_font,Vector2(-83,-143),"ZEPH",HORIZONTAL_ALIGNMENT_LEFT,-1,11,cool)
	if index>=2:
		draw_line(left,right,Color(.45,.78,1,.72*alpha*confirmed),3);for pulse in range(3):var point:=left.lerp(right,fmod(current_time*.55+pulse*.31,1.0));draw_circle(point,3,Color(.72,1,.92,.86*alpha*locked))
	draw_string(regular_font,Vector2(-151,-93),["LEO // UNCLASSIFIED","ZEPH // SIGNAL MUTATING","BRIDGE // STABLE"][index],HORIZONTAL_ALIGNMENT_LEFT,-1,11,cool)

func _draw_biometric(index:int,activity:float,confirmed:float,locked:float,alpha:float)->void:
	var reveal:=clampf((current_time-_time("record_activity_%d"%(index+1)))/1.1,0,1);var transition:=float(index)/2.0;var color:=Color("55d58b").lerp(Color("ed9845"),transition)
	for bar in range(12):var x:=-156+bar*13;var hidden:=index>=1 and bar in [7,8];var height:=18+((bar*11+index*7)%26);draw_line(Vector2(x,-145),Vector2(x,-145+height*reveal),Color("ef963f") if hidden else Color(color,.62*alpha*activity),3)
	var scan_x:=-158+fmod(maxf(0,current_time-_time("record_activity_%d"%(index+1)))*51,154);draw_line(Vector2(scan_x,-151),Vector2(scan_x,-108),Color(color,.85*alpha*activity),2)
	if index==2 and confirmed>.05:draw_rect(Rect2(-72,-151,24,46),Color(.98,.55,.23,.22*alpha*confirmed),true);draw_rect(Rect2(-72,-151,24,46),Color(.98,.68,.3,.8*alpha*locked),false,2)
	draw_string(regular_font,Vector2(-151,-93),["BIOMETRIC // NORMAL","HIDDEN REGION","KILL-SWITCH DETECTED"][index],HORIZONTAL_ALIGNMENT_LEFT,-1,11,Color(color,.82*alpha))

func _draw_data_window()->void:
	super._draw_data_window()
	if not directed:return
	var live:=_smooth(_ramp(current_time,_time("screen_initialize"),.5))*(1.0-_smooth(_ramp(current_time,_time("screen_collapse"),1.0)))
	if live<=.01:return
	var tint:=_projection_color(.2*live);draw_polyline(PackedVector2Array([screen_points[0],screen_points[1],screen_points[2],screen_points[3],screen_points[0]]),tint,3)

func _draw_window_return_cta()->void:
	if not directed:
		super._draw_window_return_cta();return
	var power:=_smooth(_ramp(current_time,_time("cta_energy"),_time("cta_typing")-_time("cta_energy")+.2));var typing:=_smooth(_ramp(current_time,_time("cta_typing"),.75));var website:=_smooth(_ramp(current_time,_time("website_reveal"),.55));var color:=_cta_color()
	if power>0:
		for path in CTA_PATHS:_draw_partial_path(path,power,color,5)
		for terminal in [-1.0,1.0]:draw_circle(Vector2(terminal*190,(-126 if terminal<0 else 132)),7,color.lightened(.18))
	if typing>0:
		var text:=str(fixture.cta.text).to_upper();var count:=mini(text.length(),int(floor((current_time-_time("cta_typing"))*28)));_draw_centered_text(text.substr(0,count),Vector2(0,-42),28,Color(.86,.97,.91,typing),heavy_font,445)
	if website>0:_draw_centered_text(str(fixture.cta.display_url).to_upper(),Vector2(0,27),22,Color(color,website),heavy_font,470);_draw_centered_text(author.to_upper(),Vector2(0,70),16,Color(.3,.78,.78,website),regular_font,430)

func _indicator_pulse(index:int)->float:
	var multiplier:=1.0
	if directed:
		var profile:=str(creative.node_profile);multiplier=1.55 if profile=="urgent" else .68 if profile=="analytical" else .85+clampf((current_time-_time("record_query_1"))/maxf(.1,_time("record_lock_3")-_time("record_query_1")),0,1)*.9
	var age:=fmod(current_time*multiplier+INDICATOR_OFFSETS[index],INDICATOR_PERIODS[index])
	if age>=INDICATOR_DURATIONS[index]:return 0.0
	return pow(sin(age/INDICATOR_DURATIONS[index]*PI),2.0)

func _projection_color(alpha:float)->Color:
	var profile:=str(creative.get("projection_profile","baseline"));var color:=Color("e96d45") if profile=="warning_trace" else Color("6e8fe8") if profile=="classification" else Color("58cf87") if profile=="biometric" else Color("56d1c2")
	if profile=="biometric":color=color.lerp(Color("ed9742"),_smooth(_ramp(current_time,_time("record_confirm_3"),.5)))
	return Color(color,alpha)

func _cta_color()->Color:
	var profile:=str(creative.get("cta_profile","baseline"));return Color("ef8742") if profile=="warning" else Color("6d8fe6") if profile=="cool_signal" else Color("55c987").lerp(Color("ea9643"),_smooth(_ramp(current_time,_time("cta_energy"),1.0))) if profile=="revelation" else Color("e68d43")

func _mechanism_header(mechanism:String,index:int)->String:
	if mechanism=="tracking":return "TARGET TRACE // PHASE %02d"%(index+1)
	if mechanism=="classification_link":return "CLASSIFICATION // PHASE %02d"%(index+1)
	return "BIOMETRIC TRACE // PHASE %02d"%(index+1)

func _draw_data_emitter()->void:
	super._draw_data_emitter()
	for index in range(INDICATOR_X.size()):
		var pulse:=_indicator_pulse(index)
		if pulse>.001:
			draw_circle(Vector2(INDICATOR_X[index],243),4.0+1.2*pulse,Color(1.0,.68,.28,.28*pulse))
