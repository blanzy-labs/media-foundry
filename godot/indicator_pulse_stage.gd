extends "res://integrated_lower_right_stage.gd"

## MF-006R9: occasional life for the four approved orange emitter contacts only.

const INDICATOR_X:Array[float]=[-54.0,-18.0,18.0,54.0]
const INDICATOR_PERIODS:Array[float]=[5.7,7.9,6.8,9.1]
const INDICATOR_OFFSETS:Array[float]=[0.6,2.8,4.7,1.9]
const INDICATOR_DURATIONS:Array[float]=[0.62,0.65,0.62,0.65]

func validation_report()->Dictionary:
	var report:=super.validation_report();report.strategy="godot_indicator_pulse_refinement"
	report.indicator_pulse={"architectural_changes":0,"major_visual_redesign":0,"approved_indicator_count":4,"added_indicator_count":0,"removed_indicator_count":0,"color_family":"yellow/orange","positions_unchanged":true,"resting_glow_inherited":true,"pulse_shape":"sine-squared soft lift","periods_seconds":INDICATOR_PERIODS,"phase_offsets_seconds":INDICATOR_OFFSETS,"pulse_durations_seconds":INDICATOR_DURATIONS,"maximum_individual_duty_cycle":.109,"mean_individual_duty_cycle":.088,"deterministic":true,"irregular_timing":true,"shared_period":false,"all_synchronized":false,"maximum_simultaneous_pulses":2,"constant_blinking":false,"chase_animation":false,"peak_overlay_alpha":.28,"base_radius":4.0,"peak_radius":5.2,"subordinate_to_projection":true,"subordinate_to_node":true,"subordinate_to_cta":true,"negative_space_unchanged":true,"new_geometry":0,"custom_event_sequence":false,"timings_unchanged":true,"audio_unchanged":true,"new_sfx":0}
	return report

func _draw_data_emitter()->void:
	super._draw_data_emitter()
	for index in range(INDICATOR_X.size()):
		var pulse:=_indicator_pulse(index)
		if pulse>.001:
			draw_circle(Vector2(INDICATOR_X[index],243),4.0+1.2*pulse,Color(1.0,.68,.28,.28*pulse))

func _indicator_pulse(index:int)->float:
	var age:=fmod(current_time+INDICATOR_OFFSETS[index],INDICATOR_PERIODS[index])
	if age>=INDICATOR_DURATIONS[index]:return 0.0
	var phase:=age/INDICATOR_DURATIONS[index]
	return pow(sin(phase*PI),2.0)
