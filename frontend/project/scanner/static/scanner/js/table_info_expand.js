$(document).ready(function() {
    $(".info_table_area").hide();
    //toggle the component with class msg_body
    $(".info_table_expander").click(function()
    {
        $(this).next(".info_table_area").toggle();
        if($(this).find($('.plus_minus')).text() == "+") {
            $(this).find($('.plus_minus')).text("-");
        } else {
            $(this).find($('.plus_minus')).text("+");
        }
    });
});