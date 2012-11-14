$(document).ready(function() {
    $("#new_scan_advanced_options_hidden").hide();
    //toggle the componenet with class msg_body
    jQuery("#new_scan_advanced_options_expander").click(function()
    {
        $("#new_scan_advanced_options_hidden").slideToggle(500);
    });
});