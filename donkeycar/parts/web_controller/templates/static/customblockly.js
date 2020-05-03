Blockly.JavaScript['turn_left'] = function(block) {
  var value_angle = Blockly.JavaScript.valueToCode(block, 'Angle', Blockly.JavaScript.ORDER_ATOMIC);
  // TODO: Assemble JavaScript into code variable.
  var state = {'tele':	{
							"user":	{
									'angle': -1,
									},
							"pilot": {
									'angle': -1,
									}
						},
					'brakeon': true,
					'recording': false,
					'driveMode': "user",
					'pilot': 'None',
					'session': 'None',
					'lag': 0,
					'controlMode': 'blockly',
					'maxThrottle': 1,
					'throttleMode': 'user',
						}
  return code;
};

Blockly.Blocks['turn_right'] = {
  init: function() {
    this.appendDummyInput()
        .setAlign(Blockly.ALIGN_CENTRE)
        .appendField(new Blockly.FieldLabelSerializable("Turn right"), "T_R");
    this.appendValueInput("Angle")
        .setCheck("Number")
        .setAlign(Blockly.ALIGN_RIGHT)
        .appendField(new Blockly.FieldLabelSerializable("Angle: (0 - 1)"), "angle");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(230);
 this.setTooltip("");
 this.setHelpUrl("");
  }
};
Blockly.JavaScript['turn_right'] = function(block) {
  var value_angle = Blockly.JavaScript.valueToCode(block, 'Angle', Blockly.JavaScript.ORDER_ATOMIC);
  // TODO: Assemble JavaScript into code variable.

  return code;
};

Blockly.Blocks['go_backward'] = {
  init: function() {
    this.appendDummyInput()
        .setAlign(Blockly.ALIGN_CENTRE)
        .appendField(new Blockly.FieldLabelSerializable("Go_backward"), "G_B");
    this.appendValueInput("Throttle")
        .setCheck("Number")
        .setAlign(Blockly.ALIGN_RIGHT)
        .appendField(new Blockly.FieldLabelSerializable("Throttle: (0 - 1)"), "throttle");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(230);
 this.setTooltip("");
 this.setHelpUrl("");
  }
};
Blockly.JavaScript['go_backward'] = function(block) {
  var value_throttle = Blockly.JavaScript.valueToCode(block, 'Throttle', Blockly.JavaScript.ORDER_ATOMIC);
  // TODO: Assemble JavaScript into code variable.
 
  return code;
};

Blockly.Blocks['go_forward'] = {
  init: function() {
    this.appendDummyInput()
        .setAlign(Blockly.ALIGN_CENTRE)
        .appendField(new Blockly.FieldLabelSerializable("Go forward"), "G_F");
    this.appendValueInput("Throttle")
        .setCheck("Number")
        .setAlign(Blockly.ALIGN_RIGHT)
        .appendField(new Blockly.FieldLabelSerializable("Throttle: (0 - 1)"), "throttle");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(230);
 this.setTooltip("");
 this.setHelpUrl("");
  }
};
Blockly.JavaScript['go_forward'] = function(block) {
  var value_throttle = Blockly.JavaScript.valueToCode(block, 'Throttle', Blockly.JavaScript.ORDER_ATOMIC);
  // TODO: Assemble JavaScript into code variable.
 
  return code;
};