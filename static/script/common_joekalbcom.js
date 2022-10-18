function initializeNavbarDropdown() {

  $('#navbar-dropdown-content').addClass("invisible");

  $('#navbar-dropdown').click(function(e){
    toggleNavbarContentVisibility();
    e.stopPropagation();
  });

  $('#navbar-dropdown').keyup(function(e) {
    //ENTER key
    if (e.keyCode == 13) {
      toggleNavbarContentVisibility();
    }
  });

  $('#navbar-dropdown-home').click(function(e) {
    gotoHome();
  });

  $('#navbar-dropdown-home').keyup(function(e) {
    //ENTER key
    if (e.keyCode == 13) {
      gotoHome();
    }
  });

  $('#navbar-dropdown-about').click(function(e) {
    gotoAbout();
  });

  $('#navbar-dropdown-about').keyup(function(e) {
    //ENTER key
    if (e.keyCode == 13) {
      gotoAbout();
    }
  });

  $('#navbar-dropdown-experience').click(function(e) {
    gotoExperience();
  });

  $('#navbar-dropdown-experience').keyup(function(e) {
    //ENTER key
    if (e.keyCode == 13) {
      gotoExperience();
    }
  });

  $('#navbar-dropdown-contact').click(function(e) {
    gotoContact();
  });

  $('#navbar-dropdown-contact').keyup(function(e) {
    //ENTER key
    if (e.keyCode == 13) {
      gotoContact();
    }
  });

  $(document).click(function(e){
    $('#navbar-dropdown-content').addClass("invisible");
  });
}

function toggleNavbarContentVisibility() {
  $('#navbar-dropdown-content').toggleClass("invisible");
}

function gotoHome() {
  window.location.href = "/dev/index.html";
}

function gotoAbout() {
  window.location.href = "/dev/about.html";
}

function gotoExperience() {
  window.location.href = "/dev/experience.html";
}

function gotoContact() {
  window.location.href = "/dev/contact.html";
}
