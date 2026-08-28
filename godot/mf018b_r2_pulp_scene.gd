class_name MF018BR2PulpScene
extends "res://mf018b_r1_pulp_scene.gd"

func render_svg(time_value:float,camera_progress:float=0.0,diagnostic:bool=false)->String:
	# The removed right-side valve must not leave disconnected steam behind.
	var preserved_pressure:=pressure;pressure=0.0
	var svg:=super.render_svg(time_value,camera_progress,diagnostic)
	pressure=preserved_pressure
	# Remove only the large-machine pipe/lever/valve assembly. No replacement prop is added.
	svg=svg.replace("<path d='M654 854 H710 V927' fill='none' stroke='#07100f' stroke-width='25'/>","")
	svg=svg.replace("<path d='M654 848 H710 V927' fill='none' stroke='#587c70' stroke-width='4'/>","")
	svg=svg.replace("<circle cx='710' cy='931' r='18' fill='#10241f' stroke='#c0a257' stroke-width='4'/>","")
	# Keep the lower control-face fill but remove its inner outline and redundant top border.
	svg=svg.replace("<path id='r1_control_panel_clean' d='M57 744 L224 744 L235 947 L52 975 Z' fill='#0a1a17' stroke='#40756a' stroke-width='3'/>","<path id='r2_control_panel_clean' d='M57 744 L224 744 L235 947 L52 975 Z' fill='#0a1a17' stroke='none'/>")
	svg=svg.replace("<path d='M68 752 H219' stroke='#9b8345' stroke-width='3'/>","")
	return svg
