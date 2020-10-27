(function($) {
    $(document).ready(function () {
 
        var persistedval = "";
        
        if ($(document).find("#tvod_form").length != 0) { 
            //alert('tvod_form is present');
            if (window.sessionStorage) {
                //alert("We have session storage!");

                if (sessionStorage.refresh){
                    stored_variable = sessionStorage.getItem('refresh'); 
                    if(stored_variable == "todo") {
                        sessionStorage.setItem("refresh", "done");
                        //persistedval = sessionStorage.getItem("refresh");
                        //alert('stored_variable should be todo - persistedval = ' + persistedval);
                        location.reload();
                        //alert('location.reload');

                    } else if (stored_variable == "done") {
                        sessionStorage.setItem("refresh", "todo");
                        //persistedval = sessionStorage.getItem("refresh");
                        //alert('stored_variable should be todo - persistedval = ' + persistedval);
                        //location.reload();
                        //alert('!! not location.reload');
                    } else {
                        //alert('stored_variable not todo & not done.');
                    }
                } else {
                    //alert('stored_variable not todo & not done.');
                    location.reload();
                    //alert('location.reload');
                    sessionStorage.setItem("refresh", "done");
                    //persistedval = sessionStorage.getItem("refresh");
                    //alert('stored_variable should be done - persistedval = ' + persistedval);
                }
            }

        } else if ($(document).find("#category_form").length != 0) {
            //alert('category_form is present');
            if (window.sessionStorage) {
                //alert("We have session storage!");

                if (sessionStorage.redo){
                    stored_variable = sessionStorage.getItem('redo'); 
                    if(stored_variable == "todo") {
                        sessionStorage.setItem("redo", "done");
                        //persistedval = sessionStorage.getItem("redo");
                        //alert('stored_variable should be todo - persistedval = ' + persistedval);
                        location.reload();
                        //alert('location.reload');

                    } else if (stored_variable == "done") {
                        sessionStorage.setItem("redo", "todo");
                        //persistedval = sessionStorage.getItem("redo");
                        //alert('stored_variable should be todo - persistedval = ' + persistedval);
                        //alert('!! not location.reload');
                    } else {
                        //alert('stored_variable not todo & not done.');
                    }
                } else {
                    //alert('stored_variable not todo & not done.');
                    location.reload();
                    //alert('location.reload');
                    sessionStorage.setItem("redo", "done");
                    //persistedval = sessionStorage.getItem("redo");
                    //alert('stored_variable should be done - persistedval = ' + persistedval);
                }
            }
        }

    });
})(django.jQuery);



