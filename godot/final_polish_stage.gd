extends "res://live_investigation_stage.gd"

## MF-006R6: motion, projection, transition, CTA, and cell polish only.

const CTA_PATHS:Array=[
	[Vector2(-330,-82),Vector2(-230,-82),Vector2(-230,-126),Vector2(-190,-126)],
	[Vector2(330,88),Vector2(230,88),Vector2(230,132),Vector2(190,132)]
]

func configure(source_fixture:Dictionary,source_timeline:Dictionary,source_layouts:Dictionary,source_heavy:Font,source_regular:Font)->Dictionary:
	var result:=super.configure(source_fixture,source_timeline,source_layouts,source_heavy,source_regular)
	if result.get("result")!="PASS":return result
	for id in ["overload_pulse_1","overload_pulse_2","record_hold_1","record_reset_1","record_hold_2","record_reset_2","record_hold_3"]:
		if _time(id)>duration:return {"result":"FAIL","error":"MF006R6_SCENE_CONFIG_FAILED: missing polish event "+id}
	return {"result":"PASS"}

func validation_report()->Dictionary:
	var report:=super.validation_report();report.strategy="godot_final_polish_refinement"
	report.final_motion_polish={"architectural_changes":0,"new_visual_metaphors":0,"legibility_gain_target_percent":15,"simon":{"moving_acquisition":true,"completion_state":true,"subtle_hold_motion":true},"leo_zeph":{"traveling_bridge_signal":true,"pulse_count":3,"stable_connection":true},"biometrics":{"scan_traversal":true,"hidden_segment_count":1,"completion_illumination":true}}
	report.node_overload_refinement.r6_pulse_events=2;report.node_overload_refinement.r5_duration_preserved=true;report.node_overload_refinement.capacity_acceleration=true
	report.background_cells.breathing_count=6;report.background_cells.deterministic_phase_offsets=true;report.background_cells.hierarchy_subordinate=true;report.background_cells.green_emphasis=.33
	report.projection_physicality={"edge_shimmer":true,"scanline_drift":true,"brightness_variation_max":.035,"text_transform_jitter":0,"reading_phase_stable":true,"refresh_emphasis_only":true}
	report.record_transitions={"completion_holds":3,"reset_events":2,"same_surface":true,"supporting_data_decay":true,"blank_interval_max":.15}
	report.cta.energy_packets_visible=true;report.cta.packet_paths=2;report.cta.packets_follow_defined_paths=true;report.cta.text_then_url=true;report.cta.final_stable_time=_time("website_reveal")+.55;report.cta.final_hold=duration-(_time("website_reveal")+.55);report.cta.major_motion_stops_after=_time("cta_settle")
	report.screen_timeline.hold_1=_time("record_hold_1");report.screen_timeline.reset_1=_time("record_reset_1");report.screen_timeline.hold_2=_time("record_hold_2");report.screen_timeline.reset_2=_time("record_reset_2");report.screen_timeline.hold_3=_time("record_hold_3")
	report.audio_visual_contract={"event_specific_confirmations":3,"refresh_cues":2,"cta_resolve_cue":1,"production_narration_alignment":"BLOCKED_PRODUCTION_VOICE"};report.text_hidden_motion_events=36
	return report

func _draw_window_chamber()->void:
	super._draw_window_chamber()
	var selected:=0
	for cell in accent_cells:
		if selected>=6:break
		var row:int=int(cell)/6;var column:int=int(cell)%6;var x:=-320.0+column*108.0+(10.0 if row%2 else 0.0);var y:=-520.0+row*118.0;var central:=column in [2,3] and row in [2,3,4];var phase:=float((int(cell)*37)%101)/101.0*TAU;var breath:=.018+.016*(.5+.5*sin(current_time*(.31+selected*.025)+phase));var color:Color=ACCENT_COLORS[int(accent_cells[cell])];if int(accent_cells[cell])==1:color=Color("3ebd76");breath+=.02
		draw_rect(Rect2(x+8,y+8,86,96),Color(color,breath*(.45 if central else 1.0)),true);selected+=1

func _draw_window_circuits()->void:
	super._draw_window_circuits()
	var overload_age:=current_time-_time("overload")
	if overload_age>=0 and current_time<_time("spark_burst"):
		var compression:=.5+.5*sin(overload_age*17.5);draw_arc(NODE,18+compression*9,0,TAU,30,Color(.75,1,.91,.38+.35*compression),4)

func _draw_record_content(index:int,alpha:float)->void:
	super._draw_record_content(index,alpha)
	var activity_start:=_time("record_activity_%d"%(index+1));var confirm_start:=_time("record_confirm_%d"%(index+1));var confirmed:=_smooth(_ramp(current_time,confirm_start,.25));var hold:=_smooth(_ramp(current_time,_time("record_hold_%d"%(index+1)),.22));var fade:=1.0
	if index<2:fade=1.0-_smooth(_ramp(current_time,_time("record_reset_%d"%(index+1)),.25))
	if index==0:
		var acquire:=clampf((current_time-activity_start)/1.0,0,1);var target:=Vector2(-131+acquire*63,-127+sin(acquire*PI)*8);var ring:=13+2*sin(current_time*4.2)*hold;draw_arc(target,ring,0,TAU,16,Color(1,.46,.31,.65*alpha*confirmed*fade),2);draw_circle(target,3,Color(1,.72,.48,.8*alpha*confirmed*fade));if confirmed>.6:draw_rect(Rect2(-156,-106,238,22),Color(.018,.095,.11,.94*alpha),true);draw_string(regular_font,Vector2(-151,-91),"SUBJECT TRACE // LOCKED",HORIZONTAL_ALIGNMENT_LEFT,-1,11,Color(1,.52,.34,.78*alpha))
	elif index==1:
		var left:=Vector2(-130,-125);var right:=Vector2(-70,-125);var bridge_age:=maxf(0,current_time-(activity_start+.72));for pulse in range(3):var travel:=clampf(bridge_age*1.15-pulse*.34,0,1);var point:=left.lerp(right,travel);draw_circle(point,4,Color(.72,1,.9,.78*alpha*fade*(1.0 if travel<1 else confirmed)))
	else:
		var scan:=clampf((current_time-activity_start)/1.15,0,1);var x:=-155+scan*84;draw_line(Vector2(x,-151),Vector2(x,-116),Color(.72,1,.86,.78*alpha*fade),3);if confirmed>0:draw_rect(Rect2(-109,-149,18,31),Color(.98,.55,.25,.18*alpha*confirmed),true);draw_rect(Rect2(-109,-149,18,31),Color(.98,.68,.3,.8*alpha*confirmed),false,2)

func _draw_data_window()->void:
	super._draw_data_window()
	var initialize:=_smooth(_ramp(current_time,_time("screen_initialize"),.55));var collapse:=_smooth(_ramp(current_time,_time("screen_collapse"),_time("energy_reclaimed")-_time("screen_collapse")));var alpha:=initialize*(1.0-collapse)
	if alpha<=.01:return
	var reading:=current_time>=_time("record_typing_1") and current_time<_time("record_hold_3");var refresh:=0.0
	for index in range(2):var reset:=_time("record_reset_%d"%(index+1));var age:=current_time-reset;if age>=0 and age<.35:refresh=maxf(refresh,1.0-age/.35)
	var shimmer:=(.035 if reading else .08)+refresh*.09;var drift:=sin(current_time*2.7)*1.2;draw_line(screen_points[0]+Vector2(drift,0),screen_points[1]+Vector2(-drift,0),Color(.52,1,.91,shimmer*alpha),2);draw_line(screen_points[2]+Vector2(-drift,0),screen_points[3]+Vector2(drift,0),Color(.35,.9,.84,shimmer*.7*alpha),2)
	if refresh>0:
		for line in range(4):var y:=-250+line*73+fmod(current_time*38,18);draw_line(Vector2(-190,y),Vector2(185,y+7),Color(.5,1,.9,.08*refresh*alpha),2)

func _draw_window_return_cta()->void:
	super._draw_window_return_cta()
	var start:=_time("cta_energy");var end:=_time("cta_typing");var active:=_smooth(_ramp(current_time,start,.25))*(1.0-_smooth(_ramp(current_time,end+.55,.5)))
	if active<=0:return
	for path_index in range(CTA_PATHS.size()):
		var path:Array=CTA_PATHS[path_index]
		for packet in range(3):var travel:=fmod(maxf(0,current_time-start)*1.25+packet*.3+path_index*.12,1.0);var point:=_point_on_path(path,travel);draw_rect(Rect2(point-Vector2(4,4),Vector2(8,8)),Color(.98,.62,.25,.85*active),true)
