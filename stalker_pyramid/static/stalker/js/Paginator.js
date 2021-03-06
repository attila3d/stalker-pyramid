// Stalker Pyramid
// Copyright (C) 2013 Erkan Ozgur Yilmaz
//
// This file is part of Stalker Pyramid.
//
// This library is free software; you can redistribute it and/or
// modify it under the terms of the GNU Lesser General Public
// License as published by the Free Software Foundation;
// version 2.1 of the License.
//
// This library is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
// Lesser General Public License for more details.
//
// You should have received a copy of the GNU Lesser General Public
// License along with this library; if not, write to the Free Software
// Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

try {
    var doT = require('../../doT/doT.min');
    var jQuery = require('../../jquery/jquery-2.0.3.min');
} catch (e) {}


(function ($) {
    'use strict';

    /**
     * Page class
     * 
     * @param options
     * @constructor
     */
    var Page = function (options) {
        options = $.extend({
            number: null,
            prev_page: null,
            next_page: null,
            active: false,
            disabled: false,
            callback: function () {}
        }, options);

        this.number = options.number;
        this.prev_page = options.prev_page;
        this.next_page = options.next_page;
        this.disabled = options.disabled;
        this.active = options.active;
        this.callback = function () {};
    };

    /**
     * Draws itself
     */
    Page.prototype.to_html = function () {
        var template = '<li>';
        if (this.active) {
            template = '<li class="active">';
        }
        template += '<a href="#">' + this.number + '</a></li>';
        return template;
    };

    /**
     * PageManager class
     * 
     * @param options
     * @constructor
     */
    var PageManager = function (options) {
        this.pages = [];
        this.shown_pages = [];
        this.current_page = null;
        this.max_number_of_page_shortcuts = 5;
    };

    Object.defineProperty(
        PageManager.prototype,
        'number_of_pages',
        {
            get: function () {
                return this.pages.length;
            }
        }
    );

    var container = null;
    var number_of_pages = 0;
    var number_of_items = 0;
    var items_per_page = 10;
    var current_page = 0;
    var max_number_of_page_shortcuts = 5;
    var callback = function () {};
    var pages = [];
    var pages_shown = [];

    var main_template = '<ul>' +
        '    <li class="disabled">' +
        '        <a href="#">' +
        '            <i class="icon-double-angle-left"></i>' +
        '        </a>' +
        '    </li>' +
        '    {{~ it.pages :p:i }}' +
        '    <li>' +
        '        <a href="#">{{=p}}</a>' +
        '    </li>' +
        '    {{~}}' +
        '    <li>' +
        '        <a href="#">' +
        '            <i class="icon-double-angle-right"></i>' +
        '        </a>' +
        '    </li>' +
        '</ul>';

    var main_template_function = doT.template(main_template);

    $.fn.paginator = function (options) {
        options = options || {};
        container = this;

        var settings = $.extend({
            number_of_items: number_of_items,
            items_per_page: items_per_page,
            current_page: current_page,
            max_number_of_page_shortcuts: max_number_of_page_shortcuts
        }, options);

        number_of_items = settings.number_of_items;
        items_per_page = settings.items_per_page;
        current_page = settings.current_page;
        max_number_of_page_shortcuts = settings.max_number_of_page_shortcuts;

        $.fn.paginator.initialize(options);
        return this;
    };


    /**
     * Initializes the paginator
     * 
     * @param options
     * @private
     */
    $.fn.paginator.initialize = function () {
        $.fn.paginator.get_pages();
        $.fn.paginator.get_pages_shown();
        $.fn.paginator.render_page_icons();
    };

    /**
     * returns an array of pages
     * 
     * @param options
     * @returns {Array}
     */
    $.fn.paginator.get_pages = function () {
        number_of_pages = Math.ceil(number_of_items / items_per_page);
        current_page = Math.max(1, Math.min(number_of_pages, current_page));
        // get the pages
        var pages = [], i;
        for (i = 0; i < number_of_pages; i += 1) {
            pages.push(i + 1);
        }
        console.log("pages :", pages);
        return pages;
    };

    /**
     * returns an array of pages
     * 
     * @param options
     * @returns {Array}
     */
    $.fn.paginator.get_pages_shown = function () {
        var page_min = Math.floor(current_page - max_number_of_page_shortcuts / 2);
        var page_max = page_min + Math.min(number_of_pages, max_number_of_page_shortcuts) - 1;
        if (page_max >= number_of_pages) {
            page_max = number_of_pages - 1;
            page_min = Math.max(0, page_max - max_number_of_page_shortcuts);
        }

        if (page_min < 0) {
            page_min = 0;
            page_max = page_min + Math.min(number_of_pages, max_number_of_page_shortcuts) - 1;
        }

        // get the pages
        pages_shown = [];
        var i;
        for (i = page_min; i <= page_max; i += 1) {
            pages_shown.push(i + 1);
        }
    };

    $.fn.paginator.render_left_icon = function () {
        return '<li class="disabled"><a href="#"><i class="icon-double-angle-left"></i></a></li>';
    };

    $.fn.paginator.render_right_icon = function () {
        return '<li><a href="#"><i class="icon-double-angle-right"></i></a></li>';
    };

    $.fn.paginator.render_page_icon = function (page_number) {
        var template = '<li>';
        if (page_number === current_page) {
            template = '<li class="active">';
        }
        template += '<a href="#">' + page_number + '</a></li>';
        return template;
    };

    $.fn.paginator.render_page_icons = function () {
        container.find('ul').remove();
        var ul_item = $($.parseHTML('<ul></ul>'));

        var left_icon = $($.parseHTML($.fn.paginator.render_left_icon()));
        ul_item.append(left_icon);

        var page_icon = null;
        var i = null;
        for (i = 0; i < pages_shown.length; i += 1) {
            page_icon = $($.parseHTML($.fn.paginator.render_page_icon(pages_shown[i])));
            ul_item.append(page_icon);
        }
        var right_icon = $($.parseHTML($.fn.paginator.render_right_icon()));
        ul_item.append(right_icon);

        container.append(ul_item);
    };

}(jQuery));




//try {
//    module.exports.Paginator = Paginator;
//} catch (e) {}
