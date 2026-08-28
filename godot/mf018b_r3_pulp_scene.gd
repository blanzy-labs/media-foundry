class_name MF018BR3PulpScene
extends "res://mf018b_r2_pulp_scene.gd"

const DISPLAY_TITLE:="UNKNOWN PROCESS"
const DISPLAY_CTA:="TRY A WEB GAME"
const DISPLAY_URL:="rcblanzy.com/books/unknown-process"
const GLYPHS:={
	"A":["01110","10001","10001","11111","10001","10001","10001"],
	"B":["11110","10001","10001","11110","10001","10001","11110"],
	"C":["01111","10000","10000","10000","10000","10000","01111"],
	"D":["11110","10001","10001","10001","10001","10001","11110"],
	"E":["11111","10000","10000","11110","10000","10000","11111"],
	"G":["01111","10000","10000","10111","10001","10001","01111"],
	"K":["10001","10010","10100","11000","10100","10010","10001"],
	"L":["10000","10000","10000","10000","10000","10000","11111"],
	"M":["10001","11011","10101","10101","10001","10001","10001"],
	"N":["10001","11001","10101","10011","10001","10001","10001"],
	"O":["01110","10001","10001","10001","10001","10001","01110"],
	"P":["11110","10001","10001","11110","10000","10000","10000"],
	"R":["11110","10001","10001","11110","10100","10010","10001"],
	"S":["01111","10000","10000","01110","00001","00001","11110"],
	"T":["11111","00100","00100","00100","00100","00100","00100"],
	"U":["10001","10001","10001","10001","10001","10001","01110"],
	"W":["10001","10001","10001","10101","10101","10101","01010"],
	"Y":["10001","10001","01010","00100","00100","00100","00100"],
	"Z":["11111","00001","00010","00100","01000","10000","11111"],
	"-":["00000","00000","00000","11111","00000","00000","00000"],
	".":["00000","00000","00000","00000","00000","00110","00110"],
	"/":["00001","00010","00010","00100","01000","01000","10000"]
}

func _reveal_alpha(time_value:float,start:float,duration:float=.70)->float:
	var value:=clampf((time_value-start)/duration,0.0,1.0)
	return value*value*(3.0-2.0*value)

func _pixel_text(value:String,center_x:float,y:float,scale:float,color:String,opacity:float)->String:
	var upper:=value.to_upper();var advance:=6.0*scale;var width:=float(upper.length())*advance-scale;var start_x:=center_x-width*.5;var result:=""
	for index in range(upper.length()):
		var character:=upper.substr(index,1)
		if character==" ":continue
		var glyph:Array=GLYPHS.get(character,[])
		for row in range(glyph.size()):
			for column in range(5):
				if glyph[row].substr(column,1)=="1":result+="<rect x='%.2f' y='%.2f' width='%.2f' height='%.2f' fill='%s' opacity='%.3f'/>" % [start_x+index*advance+column*scale,y+row*scale,scale,scale,color,opacity]
	return result

func render_svg(time_value:float,camera_progress:float=0.0,diagnostic:bool=false)->String:
	var svg:=super.render_svg(time_value,camera_progress,diagnostic)
	# Remove the parent's unused L-shaped pipe and highlight without adding a replacement object.
	svg=svg.replace("<path d='M398 389 H356 Q334 389 334 367 V315' fill='none' stroke='#07110f' stroke-width='24'/>","")
	svg=svg.replace("<path d='M398 384 H356 Q340 384 340 367 V315' fill='none' stroke='#46766a' stroke-width='4'/>","")
	# Populate the existing upper-left machine surface in place, inside the scene transform.
	var title_alpha:=_reveal_alpha(time_value,7.10)
	var cta_alpha:=_reveal_alpha(time_value,8.35)
	var url_alpha:=_reveal_alpha(time_value,9.55,.80)
	var display:="<g id='r3_information_display'>"
	display+="<rect x='42' y='164' width='198' height='248' rx='5' fill='#020908' stroke='#315e55' stroke-width='3'/>"
	display+="<path d='M51 190 H231 M51 376 H231' stroke='#8f793c' stroke-width='2'/><circle cx='222' cy='178' r='4' fill='#e6b905' opacity='%.3f'/>" % (.22+.78*title_alpha)
	for scanline in range(7):display+="<path d='M52 %d H230' stroke='#2b5b52' stroke-opacity='.13' stroke-width='1'/>" % (208+scanline*22)
	display+=_pixel_text("UNKNOWN",141,211,3.3,"#f0d58f",title_alpha)
	display+=_pixel_text("PROCESS",141,241,3.3,"#e6b905",title_alpha)
	display+="<path d='M68 277 H214' stroke='#40756a' stroke-width='2' opacity='%.3f'/>" % title_alpha
	display+=_pixel_text("TRY A WEB GAME",141,294,2.0,"#b9d5c9",cta_alpha)
	display+=_pixel_text("RCBLANZY.COM/BOOKS/",141,329,1.45,"#e0c98b",url_alpha)
	display+=_pixel_text("UNKNOWN-PROCESS",141,350,1.45,"#e0c98b",url_alpha)
	display+="</g>"
	svg=svg.replace("</g><rect x='10' y='10'",display+"</g><rect x='10' y='10'")
	# Complete the overall sloped console perimeter; the removed lower rectangular border stays absent.
	var outline:="<path id='r3_complete_control_outline' d='M51 613 L228 575 L245 625 L240 946 L52 982 Z' fill='none' stroke='#4d887c' stroke-width='3' stroke-linejoin='round'/>"
	svg=svg.trim_suffix("</svg>")+outline+"</svg>"
	return svg
