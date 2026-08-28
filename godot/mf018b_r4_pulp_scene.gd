class_name MF018BR4PulpScene
extends "res://mf018b_r3_pulp_scene.gd"

func render_svg(time_value:float,camera_progress:float=0.0,diagnostic:bool=false)->String:
	var svg:=super.render_svg(time_value,camera_progress,diagnostic)
	# Remove the legacy partial teal stroke that sat beneath the single completed R3 perimeter.
	# Its panel-face fill remains; gauges, controls, lever, dots, and the clean perimeter are untouched.
	svg=svg.replace("<path d='M51 613 L228 575 L245 625 L235 927 L52 964 Z' fill='#0a1a17' stroke='#40756a' stroke-width='3'/>","<path id='r4_panel_face_fill' d='M51 613 L228 575 L245 625 L235 927 L52 964 Z' fill='#0a1a17' stroke='none'/>")
	return svg
