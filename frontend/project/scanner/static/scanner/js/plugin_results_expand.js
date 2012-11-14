$(document).ready(function() {
    $("#plugin_results_area").hide();
    //toggle the componenet with class msg_body
    $("#overall_plugin_results_expander").click(function()
    {
        $("#plugin_results_area").slideToggle(500);
    });
});