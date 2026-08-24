extends "res://final_polish_stage.gd"

## MF-006R7: restrained lower-right environmental balance only.

const LOWER_RIGHT_BRANCH:Array=[Vector2(338,430),Vector2(278,430),Vector2(278,356),Vector2(222,356),Vector2(222,286),Vector2(132,286)]
const LOWER_RIGHT_CELL:=Rect2(206,326,76,86)

func validation_report()->Dictionary:
	var report:=super.validation_report();report.strategy="godot_lower_right_polish_refinement"
	report.lower_right_composition={"architectural_changes":0,"major_visual_redesign":0,"secondary_branch_count":1,"branch_point_count":6,"branch_thickness":3,"main_branch_thickness":4,"resting_brightness":.24,"main_circuit_brightness":.78,"brightness_ratio":.308,"maximum_packet_count":2,"ambient_packet_count":1,"packet_duty_cycle":.24,"direction":"inward/upward toward central system","powered_cell_count":1,"powered_cell_color":"purple","powered_cell_resting_alpha":.17,"negative_space_ratio":.64,"no_major_geometry":true,"second_focal_point":false,"subordinate_to_projection":true,"subordinate_to_node":true,"subordinate_to_cta":true,"overload_response":true,"projection_response":true,"cta_response":true,"cta_orange_participation":true,"camera_unchanged":true,"timings_unchanged":true}
	report.audio_visual_contract.lower_right_new_sfx=0
	return report

func _draw_window_chamber()->void:
	super._draw_window_chamber()
	var overload:=_smooth(_ramp(current_time,_time("overload"),_time("spark_burst")-_time("overload")))*(1.0-_smooth(_ramp(current_time,_time("spark_burst"),.35)))
	var projection:=_smooth(_ramp(current_time,_time("screen_initialize"),.32))*(1.0-_smooth(_ramp(current_time,_time("title_stabilized")+.35,.45)))
	var cta:=_smooth(_ramp(current_time,_time("cta_energy"),.35))*(1.0-_smooth(_ramp(current_time,_time("cta_settle"),.55)))
	var branch_color:=Color(.15+.42*cta,.54+.12*projection,.58-.25*cta,.24+overload*.13+projection*.08+cta*.16)
	_draw_partial_path(LOWER_RIGHT_BRANCH,1.0,branch_color,3)
	# One purple infrastructure cell breaks the empty corner while most of the zone remains dark.
	var breath:=.17+.018*sin(current_time*.39+2.2)+overload*.075+projection*.035;var cell_color:=Color(.46+.35*cta,.29+.18*cta,.7-.32*cta,breath+.06*cta);draw_rect(LOWER_RIGHT_CELL,cell_color,true);draw_rect(LOWER_RIGHT_CELL.grow(-4),Color(cell_color,.13+overload*.035+cta*.04),false,3)
	var ambient_window:=fmod(current_time+1.1,5.0)<1.2 and current_time<_time("screen_collapse");var event_window:=overload>.04 or projection>.04 or cta>.04
	if ambient_window or event_window:
		var speed:=.28+overload*.72+projection*.18+cta*.42;var count:=2 if overload>.28 or cta>.35 else 1
		for packet in range(count):var travel:=fmod(current_time*speed+packet*.47,1.0);var point:=_point_on_path(LOWER_RIGHT_BRANCH,travel);var color:=Color("f2a34a") if cta>.08 else Color(.55,1,.88,.58+overload*.3);draw_rect(Rect2(point-Vector2(3.5,3.5),Vector2(7,7)),color,true)
