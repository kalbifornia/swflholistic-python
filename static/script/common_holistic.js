function popUpFeatureModal(propsJSON,tagsMapData,citiesMapData,tagsFilter,citiesFilter) {
  if (typeof(citiesFilter)==='undefined') {
    citiesFilter=[];
  }
  if (typeof(tagsFilter)==='undefined') {
    tagsFilter=[];
  }

  var propsObj = JSON.parse(propsJSON);

  var nameHTMLElement = $('#modal-resource-name');
  nameHTMLElement.empty();
  if (propsObj.name != null && propsObj.description != "") {
    nameHTMLElement.html(`<h2>${propsObj.name}</h2>`);
  }

  var descriptionHTMLElement = $('#modal-resource-field-description div.modal-resource-field-value');
  descriptionHTMLElement.empty();
  if (propsObj.description != null && propsObj.description != "") {
    descriptionHTMLElement.html(propsObj.description);
  } else {
    descriptionHTMLElement.html("N/A");
  }

  var holisticDetailsHTMLElement = $('#modal-resource-field-holistic-details div.modal-resource-field-value');
  holisticDetailsHTMLElement.empty();
  if (propsObj.why_on_wapf_list != null && propsObj.why_on_wapf_list != "") {
    holisticDetailsHTMLElement.html(propsObj.why_on_wapf_list);
  } else {
    holisticDetailsHTMLElement.html("N/A");
  }

  var websiteHTMLElement = $('#modal-resource-field-website div.modal-resource-field-value');
  websiteHTMLElement.empty();
  if (propsObj.url != null && propsObj.url != "") {
    websiteHTMLElement.html(`<a href="${propsObj.url}">${propsObj.url}</a>`);
  } else {
    websiteHTMLElement.html("N/A");
  }

  var addressHTMLElement = $('#modal-resource-field-address div.modal-resource-field-value');
  addressHTMLElement.empty();
  if (propsObj.address != null && propsObj.address != "") {
    addressHTMLElement.html(propsObj.address);
  } else {
    addressHTMLElement.html("N/A");
  }
  var phoneHTMLElement = $('#modal-resource-field-phone div.modal-resource-field-value');
  phoneHTMLElement.empty();
  if (propsObj.phone != null && propsObj.phone != "") {
    phoneHTMLElement.html(propsObj.phone);
  } else {
    phoneHTMLElement.html("N/A");
  }

  var tagsHTMLElement = $('#modal-resource-field-tags div.modal-resource-field-value');
  tagsHTMLElement.empty();
  if (propsObj.tags != null) {
    var tagURLs = [];
    for (tagIndex in propsObj.tags) {
      var tag = propsObj.tags[tagIndex];
      var tagURL = `<a href="/holistic/search?type=resource&tags=${tag}&cities=${citiesFilter.join(",")}">${tagsMapData[tag].description}</a>`;
      tagURLs.push(tagURL);
    }
    tagsHTMLElement.html(tagURLs.join(", "));
  } else {
    tagsHTMLElement.html("N/A");
  }

  var citiesHTMLElement = $('#modal-resource-field-cities div.modal-resource-field-value');
  citiesHTMLElement.empty();
  if (propsObj.areas != null) {
    var cityURLs = [];
    for (cityIndex in propsObj.areas) {
      var city = propsObj.areas[cityIndex];
      var cityURL = `<a href="/holistic/search?type=resource&cities=${city}&tags=${tagsFilter.join(",")}">${citiesMapData[city].display_name}</a>`;
      cityURLs.push(cityURL);
      console.log(cityURL);
    }
    citiesHTMLElement.html(cityURLs.join(", "));
  } else {
    citiesHTMLElement.html("N/A");
  }

  $('#resource-details-modal').removeClass("invisible");
}

$(document).ready(function() {
  $("#resource-details-modal .modal-close").click(function() {
    $("#resource-details-modal").addClass("invisible");
  });

  $(".modal").click(function() {
    $("#resource-details-modal").addClass("invisible");
  });
});
