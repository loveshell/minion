$(document).ready(function() {
    //toggle the componeent with class msg_body
    $(".details_table_expander").click(function()
    {
        $(this).next(".details_table_area").toggle();
        if($(this).find($('.plus_minus')).text() == "+") {
            $(this).find($('.plus_minus')).text("-");
        } else {
            $(this).find($('.plus_minus')).text("+");
        }
    });
});