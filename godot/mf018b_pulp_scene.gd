class_name MF018BPulpScene
extends Node2D

signal reactor_state_changed(state:String)
signal reactor_energy_changed(value:float)
signal temperature_changed(value:float)
signal containment_changed(value:float)
signal field_strength_changed(value:float)
signal pressure_changed(value:float)
signal warning_level_changed(value:float)
signal control_activated(id:String,value:float)
signal machine_warning(level:float)
signal machine_critical()
signal audio_event_requested(id:String)

const VALID_STATES := ["DORMANT","STABLE","UNSTABLE","CRITICAL"]
const CONTROL_IDS := ["coolant_dial","field_dial","containment_switch","emergency_lever"]

var seed:int=1801958
var machine_state:String="DORMANT"
var reactor_energy:float=0.03
var temperature:float=0.12
var containment:float=0.82
var field_strength:float=0.08
var pressure:float=0.10
var warning_level:float=0.02
var control_values:Dictionary={"coolant_dial":.56,"field_dial":.18,"containment_switch":0.0,"emergency_lever":0.0}

func normalized(value:float)->float:return clampf(value,0.0,1.0)
func set_reactor_energy(value:float)->void:reactor_energy=normalized(value);reactor_energy_changed.emit(reactor_energy)
func set_temperature(value:float)->void:temperature=normalized(value);temperature_changed.emit(temperature)
func set_containment(value:float)->void:containment=normalized(value);containment_changed.emit(containment)
func set_field_strength(value:float)->void:field_strength=normalized(value);field_strength_changed.emit(field_strength)
func set_pressure(value:float)->void:pressure=normalized(value);pressure_changed.emit(pressure)
func set_warning_level(value:float)->void:
	warning_level=normalized(value);warning_level_changed.emit(warning_level)
	if warning_level>=.55:machine_warning.emit(warning_level)
	if warning_level>=.90:machine_critical.emit()
func set_machine_state(value:String)->void:
	if value not in VALID_STATES:push_error("MF018B invalid machine state: "+value);return
	if value!=machine_state:
		machine_state=value;reactor_state_changed.emit(machine_state)
		if value=="UNSTABLE":audio_event_requested.emit("reactor_unstable")
		elif value=="CRITICAL":audio_event_requested.emit("critical_tease")
func set_control_value(id:String,value:float)->void:
	if id not in CONTROL_IDS:push_error("MF018B invalid control: "+id);return
	var result:=normalized(value)
	if control_values[id]!=result:
		control_values[id]=result;control_activated.emit(id,result)
		if id=="emergency_lever" and result>.5:audio_event_requested.emit("lever_clunk")
func activate_control(id:String)->void:set_control_value(id,0.0 if control_values.get(id,0.0)>.5 else 1.0)

func state_snapshot()->Dictionary:
	return {"machine_state":machine_state,"reactor_energy":reactor_energy,"temperature":temperature,
		"containment":containment,"field_strength":field_strength,"pressure":pressure,
		"warning_level":warning_level,"controls":control_values.duplicate(true)}

func _path(points:Array)->String:
	var value:=""
	for index in range(points.size()):value+=("M" if index==0 else " L")+"%.2f %.2f" % points[index]
	return value

func render_svg(time_value:float,camera_progress:float=0.0,diagnostic:bool=false)->String:
	var energy:=reactor_energy;var warning:=warning_level;var pulse:=.5+.5*sin(time_value*TAU*(1.25+warning*.9))
	var scale:=1.0+.025*clampf(camera_progress,0.0,1.0)
	var svg:="<svg xmlns='http://www.w3.org/2000/svg' width='768' height='1152' viewBox='0 0 768 1152'><defs>"
	svg+="<linearGradient id='room' x1='0' y1='0' x2='0' y2='1'><stop stop-color='#04100f'/><stop offset='.56' stop-color='#0b302d'/><stop offset='1' stop-color='#050b0a'/></linearGradient>"
	svg+="<linearGradient id='steel' x1='0' y1='0' x2='1' y2='.2'><stop stop-color='#071210'/><stop offset='.26' stop-color='#24483e'/><stop offset='.47' stop-color='#10221d'/><stop offset='.72' stop-color='#7b6937'/><stop offset='1' stop-color='#091512'/></linearGradient>"
	svg+="<linearGradient id='paint' x1='0' y1='0' x2='.8' y2='1'><stop stop-color='#24554c'/><stop offset='.55' stop-color='#102b27'/><stop offset='1' stop-color='#081310'/></linearGradient>"
	svg+="<radialGradient id='glow'><stop stop-color='#fff1a4' stop-opacity='%.3f'/><stop offset='.34' stop-color='#e5ad12' stop-opacity='%.3f'/><stop offset='1' stop-color='#d15a0a' stop-opacity='0'/></radialGradient>" % [.55+.40*energy,.18+.42*energy]
	svg+="<radialGradient id='redglow'><stop stop-color='#e13b1f' stop-opacity='.5'/><stop offset='1' stop-color='#b32010' stop-opacity='0'/></radialGradient>"
	svg+="<filter id='soft'><feGaussianBlur stdDeviation='9'/></filter><clipPath id='chamber'><rect x='425' y='317' width='205' height='500' rx='43'/></clipPath></defs>"
	svg+="<g transform='translate(384 576) scale(%.5f) translate(-384 -576)'><rect width='768' height='1152' fill='url(#room)'/>" % scale
	# Purposeful background depth: ceiling beam, cylinders, and a catwalk that stops before the hero.
	svg+="<path d='M0 94 H768 M0 122 H768' stroke='#183e38' stroke-width='9'/><path d='M0 108 H768' stroke='#9b8345' stroke-opacity='.32' stroke-width='2'/>"
	for index in range(6):
		var x:=20.0+index*126.0;var top:=150.0+float((index*53)%120)
		svg+="<rect x='%.1f' y='%.1f' width='62' height='820' rx='27' fill='#071918' stroke='#28625a' stroke-opacity='.45' stroke-width='4'/>" % [x,top]
		for band in range(5):svg+="<rect x='%.1f' y='%.1f' width='70' height='8' fill='#050b0a'/>" % [x-4.0,top+100.0+band*139.0]
	svg+="<rect x='34' y='154' width='214' height='270' fill='#040d0c' opacity='.91'/><path d='M22 434 V1017' stroke='#050b0a' stroke-width='28'/><path d='M27 434 V1017' stroke='#35685d' stroke-width='4'/><path d='M50 479 H310' stroke='#a8904c' stroke-opacity='.55' stroke-width='7'/>"
	for index in range(7):svg+="<path d='M%d 479 V438' stroke='#806f3e' stroke-width='3'/>" % (63+index*39)
	# Reactor light visibly influences floor, supports, and console edge.
	svg+="<ellipse cx='526' cy='594' rx='304' ry='456' fill='url(#glow)' opacity='%.3f' filter='url(#soft)'/>" % (.10+.34*energy)
	svg+="<path d='M310 1042 L470 820 L650 820 L768 1058 Z' fill='#d68c16' opacity='%.3f'/>" % (.01+.11*energy)
	# Refined console silhouette with sloped bonnet, pedestal, bolted panels, gauges, dials, switches, lever.
	svg+="<path d='M38 592 L236 548 L263 613 L251 956 L36 1004 Z' fill='url(#paint)' stroke='#c3a250' stroke-width='7'/><path d='M51 613 L228 575 L245 625 L235 927 L52 964 Z' fill='#0a1a17' stroke='#40756a' stroke-width='3'/>"
	svg+="<path d='M68 598 L214 568' stroke='#f1d68c' stroke-opacity='.55' stroke-width='4'/><path d='M73 746 H222 M64 882 H228' stroke='#9b8345' stroke-width='3'/>"
	var gauges:=[temperature,field_strength,containment]
	for gauge in range(3):
		var cx:=88.0+gauge*61.0;var cy:=674.0+float(gauge%2)*12.0;var angle:=deg_to_rad(220.0+215.0*float(gauges[gauge]))
		var tx:=cx+cos(angle)*21.0;var ty:=cy+sin(angle)*21.0
		svg+="<circle cx='%.1f' cy='%.1f' r='31' fill='#d9c68b' stroke='#050b0a' stroke-width='7'/><circle cx='%.1f' cy='%.1f' r='25' fill='none' stroke='#806f3e' stroke-width='2'/><path d='M%.1f %.1f L%.1f %.1f' stroke='#971d12' stroke-width='4'/><circle cx='%.1f' cy='%.1f' r='5' fill='#070c0b'/>" % [cx,cy,cx,cy,cx,cy,tx,ty,cx,cy]
	# Two rotary controls and two mechanically anchored switch/lever controls.
	for dial in range(2):
		var dx:=93.0+dial*72.0;var value:=float(control_values[["coolant_dial","field_dial"][dial]])
		var da:=deg_to_rad(135.0+270.0*value)
		svg+="<circle cx='%.1f' cy='803' r='24' fill='#1d2923' stroke='#c3a250' stroke-width='5'/><path d='M%.1f 803 L%.1f %.1f' stroke='#f1d68c' stroke-width='4'/>" % [dx,dx,dx+cos(da)*17.0,803+sin(da)*17.0]
	var switch_y:=852.0-18.0*float(control_values["containment_switch"])
	svg+="<rect x='74' y='834' width='38' height='61' rx='8' fill='#06100e' stroke='#8e793f' stroke-width='4'/><circle cx='93' cy='%.1f' r='10' fill='#e0c98b'/>" % switch_y
	var lever_x:=177.0+26.0*float(control_values["emergency_lever"])
	svg+="<circle cx='177' cy='866' r='19' fill='#101d19' stroke='#b99b4b' stroke-width='4'/><path d='M177 866 L%.1f 824' stroke='#b99b4b' stroke-width='8'/><circle cx='%.1f' cy='824' r='11' fill='#a52315'/>" % [lever_x,lever_x]
	for lamp in range(4):
		var lx:=77.0+lamp*45.0;var active:=warning>(.10+lamp*.16)
		svg+="<circle cx='%.1f' cy='927' r='12' fill='#20140c' stroke='#c1a253' stroke-width='3'/>" % lx
		if active:svg+="<circle cx='%.1f' cy='927' r='8' fill='#c62d19'/><circle cx='%.1f' cy='927' r='21' fill='url(#redglow)'/>" % [lx,lx]
	# Substantial reactor: side supports, double collar, glass boundary, pipe connections, containment base.
	svg+="<path d='M374 294 H410 V1005 H365 V928 H340 V389 H374 Z' fill='url(#steel)' stroke='#9f8847' stroke-width='6'/><path d='M646 294 H683 V390 H716 V928 H684 V1005 H640 Z' fill='url(#steel)' stroke='#9f8847' stroke-width='6'/>"
	svg+="<path d='M398 389 H356 Q334 389 334 367 V315' fill='none' stroke='#07110f' stroke-width='24'/><path d='M398 384 H356 Q340 384 340 367 V315' fill='none' stroke='#46766a' stroke-width='4'/>"
	svg+="<ellipse cx='526' cy='286' rx='186' ry='94' fill='url(#steel)' stroke='#e6b905' stroke-width='11'/><ellipse cx='526' cy='286' rx='154' ry='66' fill='#0e2722' stroke='#8f793c' stroke-width='7'/><ellipse cx='526' cy='286' rx='132' ry='46' fill='#173f36' stroke='#f0d58f' stroke-width='4'/>"
	for bolt in range(16):
		var ba:=TAU*bolt/16.0;var bx:=526.0+cos(ba)*171.0;var by:=286.0+sin(ba)*78.0
		svg+="<circle cx='%.1f' cy='%.1f' r='5' fill='#070c0b' stroke='#d0b35b' stroke-width='2'/>" % [bx,by]
	# Lamps occupy separate physical housings around the upper machine collar.
	for lamp in range(12):
		var la:=PI+lamp*PI/11.0;var lx:=526.0+cos(la)*160.0;var ly:=286.0+sin(la)*69.0
		var active:=warning>(.12+float((lamp*7)%12)/17.0)
		svg+="<circle cx='%.1f' cy='%.1f' r='13' fill='#21130b' stroke='#d0b45c' stroke-width='4'/>" % [lx,ly]
		if active:svg+="<circle cx='%.1f' cy='%.1f' r='24' fill='url(#redglow)'/><circle cx='%.1f' cy='%.1f' r='7' fill='#d9361d'/>" % [lx,ly,lx,ly]
	svg+="<rect x='413' y='306' width='226' height='535' rx='55' fill='url(#steel)' stroke='#d2b862' stroke-width='8'/><rect x='430' y='323' width='192' height='501' rx='43' fill='#071412' stroke='#e7d297' stroke-width='7'/><rect x='443' y='338' width='166' height='470' rx='33' fill='#08211d' stroke='#386a60' stroke-width='3'/>"
	# All energy remains clipped to the chamber and is driven only by exposed state.
	svg+="<g clip-path='url(#chamber)'><ellipse cx='526' cy='581' rx='120' ry='350' fill='url(#glow)' opacity='%.3f'/>" % (.24+.69*energy)
	for strand in range(13):
		var points:Array=[]
		for step in range(24):
			var y:=350.0+step*19.0;var turbulence:=13.0+50.0*energy
			var x:=526.0+sin(time_value*(1.6+strand*.045)+strand*.61+step*.52)*turbulence*(.62+float(strand%4)*.11)
			points.append([x,y])
		svg+="<path d='%s' fill='none' stroke='%s' stroke-opacity='%.3f' stroke-width='%d'/>" % [_path(points),"#f5df91" if strand%3 else "#e7b515",.24+.68*energy,2+strand%3]
	svg+="</g><path d='M394 811 H658 L690 1016 H360 Z' fill='url(#steel)' stroke='#b99d4e' stroke-width='8'/><rect x='447' y='824' width='158' height='195' fill='#07100e' stroke='#d7bd67' stroke-width='6'/>"
	for vent in range(6):svg+="<path d='M458 %d H594' stroke='#8b763d' stroke-width='4'/>" % (850+vent*27)
	# One real vent origin; steam intensity follows pressure and warning state.
	svg+="<path d='M654 854 H710 V927' fill='none' stroke='#07100f' stroke-width='25'/><path d='M654 848 H710 V927' fill='none' stroke='#587c70' stroke-width='4'/><circle cx='710' cy='931' r='18' fill='#10241f' stroke='#c0a257' stroke-width='4'/>"
	if pressure>.35:
		for puff in range(6):
			var life:=fmod(time_value*.24+float(puff)/6.0,1.0);var sx:=710.0+sin(life*5.0+puff)*9.0;var sy:=918.0-life*130.0
			svg+="<ellipse cx='%.1f' cy='%.1f' rx='%.1f' ry='%.1f' fill='#ddcfaa' opacity='%.3f'/>" % [sx,sy,8.0+life*24.0,5.0+life*17.0,(1.0-life)*.11*pressure]
	# Reusable distressed material marks and restrained atmosphere.
	for index in range(128):
		var x:=float((index*83+seed%97)%748+10);var y:=float((index*137+seed%71)%1010+70)
		svg+="<path d='M%.1f %.1f l%d %d' stroke='%s' stroke-opacity='.13' stroke-width='%d'/>" % [x,y,4+(index*13)%18,(index%5)-2,"#d4b961" if index%5 else "#020706",1+index%2]
	for index in range(18):
		var x:=280.0+fmod(float(index*73+seed%89),440.0);var y:=220.0+fmod(float(index*109)+time_value*(3.0+index%4),770.0)
		svg+="<circle cx='%.1f' cy='%.1f' r='1.5' fill='#f4da97' opacity='%.3f'/>" % [x,y,.04+.10*energy]
	svg+="<path d='M0 1045 H768 V1152 H0 Z' fill='#030807'/><path d='M0 1048 H768' stroke='#8c773e' stroke-width='4'/>"
	for index in range(9):svg+="<path d='M384 1048 L%d 1152' stroke='#31564d' stroke-opacity='.48' stroke-width='2'/>" % (index*96)
	svg+="</g><rect x='10' y='10' width='748' height='1132' fill='none' stroke='#030706' stroke-width='20'/>"
	if diagnostic:
		svg+="<g font-family='sans-serif' font-size='16' font-weight='bold'>"
		var labels:=[['coolant_dial',93,803],['field_dial',165,803],['containment_switch',93,852],['emergency_lever',203,824],['reactor_energy',526,560],['warning_ring',526,190]]
		for item in labels:
			svg+="<circle cx='%d' cy='%d' r='17' fill='none' stroke='#4ee6ff' stroke-width='3'/><path d='M%d %d L%d %d' stroke='#4ee6ff' stroke-width='2'/><rect x='%d' y='%d' width='190' height='24' fill='#031010' stroke='#4ee6ff'/><text x='%d' y='%d' fill='#e9ffff'>%s</text>" % [item[1],item[2],item[1],item[2],item[1]+30,item[2]-30,item[1]+28,item[2]-48,item[1]+34,item[2]-30,item[0]]
		svg+="</g>"
	svg+="</svg>"
	return svg
