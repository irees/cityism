// Colors: colorbrewer2.org
var colors = ['#d73027', '#fc8d59', '#fee090', '#e0f3f8', '#91bfdb', '#4575b4'].reverse();

function get_qs(name) {
    name = name.replace(/[\[]/, "\\[").replace(/[\]]/, "\\]");
    var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"),
        results = regex.exec(location.search);
    return results == null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
}

var LOS = [
  {name: ' ', label: 'No service',   min:7200, max:Infinity, color:'#ccc', opacity: 1.0, width: 1.0},
  {name: 'F', label: 'F: -',      min:3600, max:7200,     color:colors[5], opacity: 1.0, width: 1.0},
  {name: 'E', label: 'E: 60m', min:1800, max:3600,     color:colors[4], opacity: 1.0, width: 1.0},
  {name: 'D', label: 'D: 30m', min:1200, max:1800,     color:colors[3], opacity: 1.0, width: 1.0},
  {name: 'C', label: 'C: 20m', min:900,  max:1200,     color:colors[2], opacity: 1.0, width: 1.0},
  {name: 'B', label: 'B: 15m', min:600,  max:900,      color:colors[1], opacity: 1.0, width: 1.0},
  {name: 'A', label: 'A: 10m', min:-1,   max:600,      color:colors[0], opacity: 1.0, width: 1.0},
];

function seconds_to_clock(t) {
  function pad(a,b){return([1e15]+a).slice(-b)}
  var h = Math.floor(t/3600);
  var m = Math.floor((t%3600)/60);
  return pad(h,2)+':'+pad(m,2)
}

function gtfsControl(element, map) {
  this.i = 0;
  this.routes = [];
  this.element = element;
  this.map = map;
  this.layer = new L.LayerGroup().addTo(this.map);
  this.build();
}
gtfsControl.prototype.build = function() {
  var self = this;
  this.element.empty();
  $('<div style="text-align:center">UNDER DEVELOPMENT</div>').appendTo(this.element);
  
  var los = $('<div />')
    .text('Period to calculate LOS')
    .addClass('cityism-transvisor-loscontrol')
    .appendTo(this.element);
  var f = $('<form />')
    .submit(function(e) {
      e.preventDefault();
      var elem = $(this);
      var los_start = $('input[name=los_start]', elem).val();
      var los_end = $('input[name=los_end]', elem).val();
      self.redraw(parseInt(los_start)*3600, parseInt(los_end)*3600);
    })
    .css('padding', 10)
    .wrap('<div />')
    .appendTo(los);
  $('<select />').append('<option>Weekday</option>').appendTo(f);
  $('<input type="number" name="los_start" />').val(7).appendTo(f);
  $('<input type="number" name="los_end" />').val(9).appendTo(f);
  $('<input type="submit" />').val('Apply').appendTo(f);

  var legend = $('<div />')
    .appendTo(los);
  for (var i in LOS) {
    $('<span />')
    .text(LOS[i].label)
    .css('width', 50)
    .css('padding', 5)
    .css('background', LOS[i].color)
    .appendTo(legend);
  }
  
  $('<ul />').addClass('cityism-transvisor-routes').appendTo(this.element);
}
gtfsControl.prototype.load_gtfs = function(uri, redraw) {
  var self = this;
  $.getJSON(uri, function(data) {
    self.add_gtfs(uri, data, redraw);
  });
}
gtfsControl.prototype.add_gtfs = function(uri, data, redraw) {
  for (var route in data.features) {
    route = data.features[route];
    route.source = uri;
    route.i = parseInt(this.i); // index for svg elements
    this.i++;
    this.routes.push(route)
  }
  redraw = true;
  if (redraw) {
    this.redraw();
    this.fit_all();
  }
}
gtfsControl.prototype.calc_los = function(feature, start, end) {
  var start = start || 7 * 3600;
  var end = end || 9 * 3600;
  var trips = feature.properties.trips.filter(function(i) {
    return i > start && i <= end
  });
  // Buses per hour
  var headway = ((end-start)/3600 / trips.length) * 3600;
  // Find the LOS.
  for (var i in LOS) {
    if (headway > LOS[i].min && headway <= LOS[i].max) {
      return i
    }
  }
  return i
}
gtfsControl.prototype.fit_all = function() {
  var max_ne = 0;
  var max_sw = 0;
  var bounds = null;
  this.layer.eachLayer(function(i){
    if (bounds==null) {bounds=i.getBounds()}
    bounds.extend(i.getBounds());
  });
  this.map.fitBounds(bounds);
}
gtfsControl.prototype.hide_all = function() {
  $('.cityism-transvisor-route input:checkbox').trigger('off');
}
gtfsControl.prototype.show_all = function() {
  $('.cityism-transvisor-route input:checkbox').trigger('on');
}
gtfsControl.prototype.redraw = function(start, end) {
  for (var route in this.routes) {
    route = this.routes[route];
    route.los = this.calc_los(route, start, end);
  }
  this.redraw_panel();
  this.redraw_routes();
}
gtfsControl.prototype.redraw_panel = function() {
  var self = this;
  var ul = $('.cityism-transvisor-routes', this.element);
  ul.empty();
  for (var route in this.routes) {
    route = this.routes[route];
    var li = $('<li />')
      .bind('on', function(e) {
        var elem = $(this);
        var route = elem.data('route');
        $('.route-'+route.i).show();
        $('input:checkbox', elem).prop('checked', true);
      })
      .bind('off', function(e) {
        var elem = $(this);
        var route = elem.data('route');
        $('.route-'+route.i).hide();
        $('input:checkbox', elem).prop('checked', false);
      })
      .data('i', route.i)
      .data('route', route)
      .css('background', LOS[route.los].color)
      .addClass('cityism-transvisor-route')
      .appendTo(ul);
    
    $('<span />')
      .text(route.properties.name)
      .click(function(e) {
        var elem = $(this);
        var route = $(this).parent().data('route');
        var dialog = $('<div />').attr('title', 'Trips');
        var ul = $('<ul />').appendTo(dialog);
        for (var t in route.properties.trips) {
          $('<li />').text(seconds_to_clock(route.properties.trips[t])).appendTo(ul);
        }
        dialog.dialog({
          //buttons: {Ok: function() {$( this ).dialog( "close" )}}
        })
      }).appendTo(li);

    $('<input type="checkbox" checked="checked" />')
      .change(function(e) {
        var elem = $(this);
        e.preventDefault();
        if (elem.prop('checked')) {
          elem.parent().trigger('on');
        } else {
          elem.parent().trigger('off');
        }
      })
      .prependTo(li);

    $('<button />')
      .text('Show only')
      .click(function (e){
        var elem = $(this);
        var route = elem.parent().data('route');
        var bounds = route.layer.getBounds();
        self.hide_all();
        elem.parent().trigger('on');
        self.map.fitBounds(bounds);
      })
      .css('float', 'right')
      .addClass('cityism-transvisor-hover')
      .appendTo(li);
  }
}
gtfsControl.prototype.redraw_routes = function() {
  // Clear everything.
  this.layer.clearLayers();
  var routes = this.routes.slice(0).sort(function(a,b){return a.los - b.los});
  for (var route in routes) {
    route = routes[route];
    route.layer = new L.geoJson(route, {
      style: {
        color: LOS[route.los].color,
        opacity: LOS[route.los].opacity
      },
      className: 'route route-'+route.i
    }).addTo(this.layer);
  }
}






